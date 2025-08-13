"""
Processing pipeline orchestration for Bookfix.

This module provides functionality to create and run processing pipelines,
coordinating the execution of various text processing steps.
"""

from typing import TYPE_CHECKING, List, Dict, Callable, Optional

if TYPE_CHECKING:
    from .context import BookfixContext, ProcessingStep


def create_processing_pipeline() -> List['ProcessingStep']:
    """
    Create the standard processing pipeline in the correct logical order.
    
    PROCESSING ORDER (matches original bookfix.py):
    
    NON-INTERACTIVE STEPS:
    1. automatic_replacements  - Apply regex find/replace rules from .data.txt
    2. insert_periods         - Add periods to abbreviations (Mr -> M.r.)  
    3. remove_pagination      - Remove page numbers from HTML/TXT
    4. roman_numerals         - Convert Roman numerals to Arabic (IV -> 4)
    5. convert_lowercase      - Convert entire text to lowercase (optional)
    6. remove_blank_lines     - Remove empty lines and whitespace
    
    INTERACTIVE STEPS (handled separately):
    7. interactive_choices    - User selects word replacements
    8. all_caps_processing    - User decides on all-caps sequences  
    9. numbered_line_edit     - Manual editing of lines with numbers
    
    This order is important because:
    - Automatic replacements happen first to fix common issues
    - Pagination removal before roman conversion prevents false matches
    - Lowercase conversion affects subsequent interactive processing
    - Interactive steps come last for final user control
    """
    from .context import ProcessingStep
    from .processors.automatic import apply_automatic_replacements
    from .processors.periods import insert_periods_into_abbreviations
    from .processors.pagination import remove_pagination
    from .processors.roman import convert_roman_numerals
    from .processors.lowercase import convert_to_lowercase
    from .processors.blanklines import remove_blank_lines
    
    return [
        # Non-interactive processing steps (in original order)
        ProcessingStep(
            name='automatic_replacements',
            processor=apply_automatic_replacements,
            description='Apply automatic find/replace rules',
            requires_interaction=False
        ),
        ProcessingStep(
            name='insert_periods',
            processor=insert_periods_into_abbreviations,
            description='Insert periods into abbreviations',
            requires_interaction=False
        ),
        ProcessingStep(
            name='remove_pagination',
            processor=remove_pagination,
            description='Remove pagination elements',
            requires_interaction=False
        ),
        ProcessingStep(
            name='roman_numerals',
            processor=convert_roman_numerals,
            description='Convert Roman numerals to Arabic',
            requires_interaction=False
        ),
        ProcessingStep(
            name='convert_lowercase',
            processor=convert_to_lowercase,
            description='Convert entire text to lowercase',
            requires_interaction=False,
            enabled=False
        ),
        ProcessingStep(
            name='remove_blank_lines',
            processor=remove_blank_lines,
            description='Remove blank lines',
            requires_interaction=False,
            enabled=False
        ),
        # Interactive steps handled separately after non-interactive pipeline
        ProcessingStep(
            name='interactive_choices',
            processor=lambda ctx: ctx,  # Will be handled separately
            description='Interactive word choices',
            requires_interaction=True
        ),
        ProcessingStep(
            name='all_caps_processing',
            processor=lambda ctx: ctx,  # Will be handled separately
            description='Process all-caps sequences',
            requires_interaction=True
        ),
        ProcessingStep(
            name='numbered_line_edit',
            processor=lambda ctx: ctx,  # Will be handled separately
            description='Edit lines with numbers',
            requires_interaction=True
        )
    ]


def run_processing_pipeline(ctx: 'BookfixContext', enabled_steps: Dict[str, bool],
                          progress_callback: Optional[Callable[[int, int, str], None]] = None) -> 'BookfixContext':
    """
    Run the processing pipeline with enabled steps.
    
    Args:
        ctx: BookfixContext to process
        enabled_steps: Dictionary mapping step names to enabled status
        progress_callback: Optional callback for progress updates (current, total, description)
        
    Returns:
        Updated BookfixContext after processing
    """
    from .logging import log_message
    
    pipeline = create_processing_pipeline()

    for i, step in enumerate(pipeline):
        if enabled_steps.get(step.name, False) and not step.requires_interaction:
            log_message(f"Starting {step.description}...")
            ctx = step.processor(ctx)

            if progress_callback:
                progress_callback(i + 1, len(pipeline), step.description)

    return ctx


def run_processing(ctx: 'BookfixContext', enabled_steps: Dict[str, bool],
                  progress_callback: Optional[Callable[[int, int, str], None]] = None,
                  status_callback: Optional[Callable[[str], None]] = None,
                  interactive_callbacks: Optional[Dict[str, Callable]] = None) -> 'BookfixContext':
    """
    Run the complete processing workflow including interactive steps.
    
    Args:
        ctx: BookfixContext to process
        enabled_steps: Dictionary mapping step names to enabled status
        progress_callback: Optional callback for progress updates
        status_callback: Optional callback for status messages
        interactive_callbacks: Optional dictionary of callbacks for interactive processing
        
    Returns:
        Updated BookfixContext after all processing
    """
    from .logging import log_message
    from .processors.lowercase import apply_upper_to_lower
    
    log_message("Starting run_processing with modular pipeline.")

    # Progress callback wrapper
    def update_progress(current: int, total: int, description: str):
        if status_callback:
            status_callback(f"Step {current}/{total}: {description}")
        if progress_callback:
            progress_callback(current, total, description)

    # Run non-interactive processing pipeline
    log_message("Starting non-interactive processing pipeline.")
    ctx = run_processing_pipeline(ctx, enabled_steps, update_progress)
    log_message("Non-interactive processing pipeline completed.")

    # Interactive Processing Steps (handled separately in logical order)

    # 1. Interactive Choices - After automatic processing, let user make word choices
    if enabled_steps.get('interactive_choices', False):
        log_message("Interactive Choices enabled - GUI will handle this step")
        if status_callback:
            status_callback("Ready for interactive choices...")
    
    # 2. Process All-Caps Sequences - After other processing, handle caps interactively
    if enabled_steps.get('all_caps_processing', False):
        log_message("All-caps processing enabled")

        # Pre-apply UPPER_TO_LOWER rules
        if status_callback:
            status_callback("Applying auto-lowercase rules...")
        
        if ctx.lowercase_set:
            mapping = {word: word.lower() for word in ctx.lowercase_set}
            ctx = apply_upper_to_lower(ctx, mapping)
            log_message(f"Auto-lowercased {len(mapping)} words from lowercase_set: {list(mapping.keys())}")

        if status_callback:
            status_callback("Ready for all-caps interactive processing...")
        log_message("All-caps processing ready for GUI interaction")
    
    # 3. Interactive Numbered Line Edit - Final manual editing step
    if enabled_steps.get('numbered_line_edit', False):
        log_message("Numbered line editing enabled - GUI will handle this step")
        if status_callback:
            status_callback("Ready for numbered line editing...")

    # Display processing summary
    log_message("Processing Summary:")
    log_message(ctx.get_processing_summary())

    log_message("run_processing pipeline setup complete.")
    return ctx


def get_available_processors() -> List[Dict[str, any]]:
    """
    Get list of available processors with their metadata.
    
    Returns:
        List of processor dictionaries with name, description, interactive flags
    """
    pipeline = create_processing_pipeline()
    
    return [
        {
            'name': step.name,
            'description': step.description,
            'requires_interaction': step.requires_interaction,
            'enabled': step.enabled
        }
        for step in pipeline
    ]


def validate_enabled_steps(enabled_steps: Dict[str, bool]) -> Dict[str, bool]:
    """
    Validate and sanitize enabled steps dictionary.
    
    Args:
        enabled_steps: Dictionary mapping step names to enabled status
        
    Returns:
        Validated dictionary with only valid step names
    """
    pipeline = create_processing_pipeline()
    valid_step_names = {step.name for step in pipeline}
    
    return {
        name: enabled
        for name, enabled in enabled_steps.items()
        if name in valid_step_names
    }