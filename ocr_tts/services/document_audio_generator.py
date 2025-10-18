from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.cache import cache
from .tts_service import TTSService
from io import BytesIO
import re
from pydub import AudioSegment


class DocumentAudioGenerator:
    """Service for generating audio from entire document after all pages are processed"""

    def __init__(self, document):
        """
        Initialize generator with document settings

        Args:
            document: Document instance
        """
        self.document = document
        self.tts_service = TTSService(
            language=document.language,
            provider=document.tts_provider
        )

    def generate_audio(self, metadata=None):
        """
        Combine audio files from text blocks (Step 5) with optional metadata.

        Process:
        1. Get all BlockAudio instances for document (from Step 4)
        2. Load audio files from database
        3. Concatenate all audio files in order
        4. Apply metadata tags to audio file
        5. Save combined audio to document

        Args:
            metadata: Optional dict with keys: title, artist, album, date, genre, comment

        Returns:
            Document: Updated document with combined audio file
        """
        if metadata is None:
            metadata = {}
        # Cache key for progress tracking
        progress_key = f'audio_generation_progress_{self.document.id}'

        # Initialize progress
        cache.set(progress_key, {
            'status': 'starting',
            'progress': 0,
            'current_block': 0,
            'total_blocks': 0,
            'message': 'Підготовка до об\'єднання аудіо...'
        }, timeout=600)

        try:
            # Get all text blocks with audio
            text_blocks = self.document.text_blocks.order_by('block_number').prefetch_related('audio')

            if not text_blocks.exists():
                raise Exception("No text blocks found. Run Step 4 first.")

            # Check if all blocks have audio
            blocks_with_audio = [block for block in text_blocks if hasattr(block, 'audio') and block.audio]

            if len(blocks_with_audio) != text_blocks.count():
                missing_count = text_blocks.count() - len(blocks_with_audio)
                raise Exception(f"Missing audio for {missing_count} blocks. Generate block audio first.")

            total_blocks = len(blocks_with_audio)

            # Update progress
            cache.set(progress_key, {
                'status': 'loading',
                'progress': 10,
                'current_block': 0,
                'total_blocks': total_blocks,
                'message': f'Завантаження {total_blocks} аудіо блоків...'
            }, timeout=600)

            # Load audio files from database
            audio_files = []
            for i, block in enumerate(blocks_with_audio, 1):
                audio_files.append(block.audio.audio_file)

                # Update progress
                progress_percent = 10 + int((i / total_blocks) * 30)
                cache.set(progress_key, {
                    'status': 'loading',
                    'progress': progress_percent,
                    'current_block': i,
                    'total_blocks': total_blocks,
                    'message': f'Завантажено блок {i} з {total_blocks}'
                }, timeout=600)

            # Update progress - concatenating
            cache.set(progress_key, {
                'status': 'concatenating',
                'progress': 40,
                'current_block': total_blocks,
                'total_blocks': total_blocks,
                'message': 'Об\'єднання аудіо блоків...'
            }, timeout=600)

            # Concatenate audio files
            combined_audio = self._concatenate_audio_files(
                audio_files,
                self.document.tts_provider
            )

            # Apply metadata if provided
            if metadata and any(metadata.values()):
                cache.set(progress_key, {
                    'status': 'metadata',
                    'progress': 80,
                    'current_block': total_blocks,
                    'total_blocks': total_blocks,
                    'message': 'Додавання метаданих...'
                }, timeout=600)

                combined_audio = self._apply_metadata(combined_audio, metadata)

            # Update progress - saving
            cache.set(progress_key, {
                'status': 'saving',
                'progress': 95,
                'current_block': total_blocks,
                'total_blocks': total_blocks,
                'message': 'Збереження аудіокниги...'
            }, timeout=600)

            # Save combined audio
            audio_extension = '.wav' if self.document.tts_provider == 'gemini' else '.mp3'
            audio_filename = f'document_{self.document.id}_audiobook{audio_extension}'

            self.document.combined_audio_file.save(audio_filename, combined_audio, save=False)

            # Mark audio as generated
            self.document.audio_generated = True
            self.document.audio_generated_at = timezone.now()
            self.document.save()

            # Update progress - completed
            cache.set(progress_key, {
                'status': 'completed',
                'progress': 100,
                'current_block': total_blocks,
                'total_blocks': total_blocks,
                'message': 'Завершено!'
            }, timeout=600)

            return self.document

        except Exception as e:
            # Update progress - error
            cache.set(progress_key, {
                'status': 'error',
                'progress': 0,
                'current_block': 0,
                'total_blocks': 0,
                'message': f'Помилка: {str(e)}'
            }, timeout=600)
            raise

    def _concatenate_audio_files(self, audio_files, provider):
        """
        Concatenate multiple audio FileField files into one using pydub.

        Args:
            audio_files: List of Django FileField audio files
            provider: 'gtts' (MP3) or 'gemini' (WAV)

        Returns:
            ContentFile: Combined audio file
        """
        print(f"Concatenating {len(audio_files)} audio files...")

        if not audio_files:
            raise Exception("No audio files to concatenate")

        # Determine format
        format_type = 'mp3' if provider == 'gtts' else 'wav'

        # Load first audio segment
        combined = AudioSegment.from_file(audio_files[0].path, format=format_type)
        print(f"First segment duration: {len(combined)}ms")

        # Append remaining segments
        for i in range(1, len(audio_files)):
            segment = AudioSegment.from_file(audio_files[i].path, format=format_type)
            print(f"Segment {i+1} duration: {len(segment)}ms")
            combined += segment

        print(f"Total combined duration: {len(combined)}ms")

        # Export to BytesIO
        output = BytesIO()
        combined.export(output, format=format_type)
        output.seek(0)

        return ContentFile(output.read())

    def _apply_metadata(self, audio_file, metadata):
        """
        Apply metadata tags to audio file.
        Uses mutagen for MP3 files and ffmpeg for WAV files.

        Args:
            audio_file: ContentFile with audio data
            metadata: Dict with keys: title, artist, album, date, genre, comment

        Returns:
            ContentFile: Audio file with metadata
        """
        import tempfile
        import os
        import subprocess

        # Determine format and file extension
        is_mp3 = self.document.tts_provider == 'gtts'
        file_extension = '.mp3' if is_mp3 else '.wav'

        # Create temporary input file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(audio_file.read())
            temp_input_path = temp_file.name

        # Create temporary output file path
        temp_output_path = temp_input_path.replace(file_extension, f'_metadata{file_extension}')

        try:
            if is_mp3:
                # Use mutagen for MP3
                from mutagen.mp3 import MP3
                from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, COMM

                audio = MP3(temp_input_path, ID3=ID3)

                # Add ID3 tag if it doesn't exist
                try:
                    audio.add_tags()
                except Exception:
                    pass  # Tags already exist

                # Clear existing tags to avoid duplicates
                audio.tags.clear()

                # Apply metadata
                if metadata.get('title'):
                    audio.tags.add(TIT2(encoding=3, text=metadata['title']))
                if metadata.get('artist'):
                    audio.tags.add(TPE1(encoding=3, text=metadata['artist']))
                if metadata.get('album'):
                    audio.tags.add(TALB(encoding=3, text=metadata['album']))
                if metadata.get('date'):
                    audio.tags.add(TDRC(encoding=3, text=metadata['date']))
                if metadata.get('genre'):
                    audio.tags.add(TCON(encoding=3, text=metadata['genre']))
                if metadata.get('comment'):
                    audio.tags.add(COMM(encoding=3, lang='ukr', desc='desc', text=metadata['comment']))

                audio.save(v2_version=3)

                # Read back the file with metadata
                with open(temp_input_path, 'rb') as f:
                    result = ContentFile(f.read())

            else:
                # Use ffmpeg for WAV
                ffmpeg_cmd = ['ffmpeg', '-i', temp_input_path, '-y']

                # Add metadata options
                if metadata.get('title'):
                    ffmpeg_cmd.extend(['-metadata', f'title={metadata["title"]}'])
                if metadata.get('artist'):
                    ffmpeg_cmd.extend(['-metadata', f'artist={metadata["artist"]}'])
                if metadata.get('album'):
                    ffmpeg_cmd.extend(['-metadata', f'album={metadata["album"]}'])
                if metadata.get('date'):
                    ffmpeg_cmd.extend(['-metadata', f'date={metadata["date"]}'])
                if metadata.get('genre'):
                    ffmpeg_cmd.extend(['-metadata', f'genre={metadata["genre"]}'])
                if metadata.get('comment'):
                    ffmpeg_cmd.extend(['-metadata', f'comment={metadata["comment"]}'])

                # Copy codec without re-encoding
                ffmpeg_cmd.extend(['-codec', 'copy', temp_output_path])

                # Run ffmpeg
                subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

                # Read back the file with metadata
                with open(temp_output_path, 'rb') as f:
                    result = ContentFile(f.read())

            return result

        except Exception as e:
            print(f"Error applying metadata: {e}")
            # Return original file if metadata application fails
            audio_file.seek(0)
            return audio_file

        finally:
            # Clean up temporary files
            if os.path.exists(temp_input_path):
                os.remove(temp_input_path)
            if os.path.exists(temp_output_path):
                os.remove(temp_output_path)

    def _concatenate_audio_buffers(self, buffers, provider):
        """
        Concatenate multiple audio buffers into one using pydub.

        Args:
            buffers: List of BytesIO audio buffers
            provider: 'gtts' (MP3) or 'gemini' (WAV)

        Returns:
            ContentFile: Combined audio file
        """
        print(f"Concatenating {len(buffers)} audio buffers...")

        if not buffers:
            raise Exception("No audio buffers to concatenate")

        # Determine format
        format_type = 'mp3' if provider == 'gtts' else 'wav'

        # Load first audio segment
        buffers[0].seek(0)
        combined = AudioSegment.from_file(buffers[0], format=format_type)
        print(f"First segment duration: {len(combined)}ms")

        # Append remaining segments
        for i in range(1, len(buffers)):
            buffers[i].seek(0)
            segment = AudioSegment.from_file(buffers[i], format=format_type)
            print(f"Segment {i+1} duration: {len(segment)}ms")
            combined += segment

        print(f"Total combined duration: {len(combined)}ms")

        # Export to BytesIO
        output = BytesIO()
        combined.export(output, format=format_type)
        output.seek(0)

        return ContentFile(output.read())
