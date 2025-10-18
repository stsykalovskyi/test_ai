from django.utils import timezone
from django.core.cache import cache
from io import BytesIO
from pydub import AudioSegment
from .tts_service import TTSService
from ..models import BlockAudio, TextBlock


class BlockAudioGenerator:
    """Service for generating audio files for individual text blocks"""

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

    def generate_all_block_audio(self):
        """
        Generate audio for all text blocks in the document.

        Process:
        1. Get all TextBlock instances for document
        2. Generate audio for each block
        3. Store as BlockAudio with duration

        Returns:
            list: List of created BlockAudio instances
        """
        # Cache key for progress tracking
        progress_key = f'block_audio_progress_{self.document.id}'

        # Initialize progress
        cache.set(progress_key, {
            'status': 'starting',
            'progress': 0,
            'message': 'Підготовка до генерації аудіо...'
        }, timeout=600)

        try:
            # Get all text blocks
            text_blocks = TextBlock.objects.filter(document=self.document).order_by('block_number')

            if not text_blocks.exists():
                raise Exception("No text blocks found. Run Step 4 first.")

            total_blocks = text_blocks.count()

            # Update progress
            cache.set(progress_key, {
                'status': 'generating',
                'progress': 5,
                'message': f'Генерація аудіо для {total_blocks} блоків...'
            }, timeout=600)

            # Generate audio for each block ONE BY ONE
            created_audio = []
            for i, text_block in enumerate(text_blocks, 1):
                # Update progress - STARTING block generation
                progress_percent_start = int(((i - 1) / total_blocks) * 90) + 5
                cache.set(progress_key, {
                    'status': 'generating',
                    'progress': progress_percent_start,
                    'current_block': i,
                    'total_blocks': total_blocks,
                    'message': f'Генерація аудіо для блоку {i} з {total_blocks}...'
                }, timeout=600)
                print(f"[BLOCK {i}/{total_blocks}] Starting audio generation...")

                # Check if audio already exists
                if hasattr(text_block, 'audio') and text_block.audio:
                    # Skip existing audio
                    print(f"[BLOCK {i}/{total_blocks}] Audio already exists, skipping...")
                    created_audio.append(text_block.audio)
                else:
                    # Generate new audio for this block
                    block_audio = self.generate_block_audio(text_block)
                    created_audio.append(block_audio)

                # Update progress - COMPLETED block generation
                progress_percent_end = int((i / total_blocks) * 90) + 5
                cache.set(progress_key, {
                    'status': 'generating',
                    'progress': progress_percent_end,
                    'current_block': i,
                    'total_blocks': total_blocks,
                    'message': f'Блок {i} з {total_blocks} готовий'
                }, timeout=600)
                print(f"[BLOCK {i}/{total_blocks}] Completed!")

            # Update progress - completed
            cache.set(progress_key, {
                'status': 'completed',
                'progress': 100,
                'message': f'Згенеровано аудіо для {total_blocks} блоків'
            }, timeout=600)

            return created_audio

        except Exception as e:
            # Update progress - error
            cache.set(progress_key, {
                'status': 'error',
                'progress': 0,
                'message': f'Помилка: {str(e)}'
            }, timeout=600)
            raise

    def generate_block_audio(self, text_block):
        """
        Generate audio for a single text block.

        Args:
            text_block: TextBlock instance

        Returns:
            BlockAudio: Created BlockAudio instance
        """
        print(f"Generating audio for block {text_block.block_number}...")

        # Generate audio buffer
        if self.document.tts_provider == 'gtts':
            audio_buffer = self.tts_service.text_to_speech_gtts(text_block.text_content)
            audio_extension = '.mp3'
            format_type = 'mp3'
        else:  # gemini
            audio_buffer = self.tts_service.text_to_speech_gemini(
                text_block.text_content,
                voice=self.document.tts_voice
            )
            audio_extension = '.wav'
            format_type = 'wav'

        # Calculate duration using pydub
        audio_buffer.seek(0)
        audio_segment = AudioSegment.from_file(audio_buffer, format=format_type)
        duration_ms = len(audio_segment)

        # Save to BlockAudio
        audio_filename = f'block_{self.document.id}_{text_block.block_number}{audio_extension}'
        audio_buffer.seek(0)

        block_audio = BlockAudio.objects.create(
            text_block=text_block,
            duration_ms=duration_ms
        )
        block_audio.audio_file.save(audio_filename, audio_buffer, save=True)

        print(f"Block {text_block.block_number} audio saved: {duration_ms}ms")
        return block_audio

    def regenerate_block_audio(self, text_block):
        """
        Regenerate audio for a single text block.

        Args:
            text_block: TextBlock instance

        Returns:
            BlockAudio: Updated BlockAudio instance
        """
        print(f"Regenerating audio for block {text_block.block_number}...")

        # Generate audio buffer
        if self.document.tts_provider == 'gtts':
            audio_buffer = self.tts_service.text_to_speech_gtts(text_block.text_content)
            audio_extension = '.mp3'
            format_type = 'mp3'
        else:  # gemini
            audio_buffer = self.tts_service.text_to_speech_gemini(
                text_block.text_content,
                voice=self.document.tts_voice
            )
            audio_extension = '.wav'
            format_type = 'wav'

        # Calculate duration using pydub
        audio_buffer.seek(0)
        audio_segment = AudioSegment.from_file(audio_buffer, format=format_type)
        duration_ms = len(audio_segment)

        # Update or create BlockAudio
        if hasattr(text_block, 'audio') and text_block.audio:
            block_audio = text_block.audio
            # Delete old audio file
            if block_audio.audio_file:
                block_audio.audio_file.delete(save=False)
        else:
            block_audio = BlockAudio(text_block=text_block)

        # Save new audio file
        audio_filename = f'block_{self.document.id}_{text_block.block_number}{audio_extension}'
        audio_buffer.seek(0)
        block_audio.audio_file.save(audio_filename, audio_buffer, save=False)
        block_audio.duration_ms = duration_ms
        block_audio.regenerated_at = timezone.now()
        block_audio.save()

        print(f"Block {text_block.block_number} audio regenerated: {duration_ms}ms")
        return block_audio
