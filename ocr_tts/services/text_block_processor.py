import re
from django.core.cache import cache
from ..models import TextBlock


class TextBlockProcessor:
    """Service for dividing final text into blocks and storing to database (Step 4)"""

    def __init__(self, document):
        """
        Initialize processor with document

        Args:
            document: Document instance with final_text
        """
        self.document = document

    def process_text_blocks(self):
        """
        Divide final_text into blocks and store to database.

        Process:
        1. Read final_text from database (generated in Step 3)
        2. Split by dividers to get individual page text blocks
        3. Store each block as TextBlock in database
        4. Clear existing blocks if regenerating

        Returns:
            list: List of created TextBlock instances
        """
        if not self.document.final_text:
            raise Exception("No final text found. Generate text first (Step 3).")

        # Cache key for progress tracking
        progress_key = f'text_block_progress_{self.document.id}'

        # Initialize progress
        cache.set(progress_key, {
            'status': 'starting',
            'progress': 0,
            'message': 'Підготовка до розділення тексту...'
        }, timeout=600)

        try:
            # Split text by page dividers
            combined_text = self.document.final_text
            page_blocks = re.split(r'===PAGE_\d+===\n?', combined_text)
            page_blocks = [block.strip() for block in page_blocks if block.strip()]

            if not page_blocks:
                raise Exception("No text blocks found after splitting")

            total_blocks = len(page_blocks)

            # Update progress
            cache.set(progress_key, {
                'status': 'processing',
                'progress': 10,
                'message': f'Збереження {total_blocks} текстових блоків...'
            }, timeout=600)

            # Get existing blocks with audio to preserve them
            existing_blocks = {block.block_number: block for block in TextBlock.objects.filter(document=self.document)}

            # Update or create TextBlock instances
            created_blocks = []
            for i, text_content in enumerate(page_blocks, 1):
                if i in existing_blocks:
                    # Update existing block, preserving its audio relationship
                    text_block = existing_blocks[i]
                    text_block.text_content = text_content
                    text_block.save()
                else:
                    # Create new block
                    text_block = TextBlock.objects.create(
                        document=self.document,
                        block_number=i,
                        text_content=text_content
                    )
                created_blocks.append(text_block)

                # Update progress
                progress_percent = 10 + int((i / total_blocks) * 80)
                cache.set(progress_key, {
                    'status': 'processing',
                    'progress': progress_percent,
                    'message': f'Збережено блок {i} з {total_blocks}'
                }, timeout=600)

            # Delete any extra blocks that no longer exist (if total blocks decreased)
            blocks_to_delete = [num for num in existing_blocks.keys() if num > total_blocks]
            if blocks_to_delete:
                TextBlock.objects.filter(
                    document=self.document,
                    block_number__in=blocks_to_delete
                ).delete()

            # Update progress - completed
            cache.set(progress_key, {
                'status': 'completed',
                'progress': 100,
                'message': f'Розділено на {total_blocks} блоків'
            }, timeout=600)

            return created_blocks

        except Exception as e:
            # Update progress - error
            cache.set(progress_key, {
                'status': 'error',
                'progress': 0,
                'message': f'Помилка: {str(e)}'
            }, timeout=600)
            raise
