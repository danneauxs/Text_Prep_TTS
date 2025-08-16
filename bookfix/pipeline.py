"""
Processing pipeline for Bookfix.

This module coordinates the execution of various text processing steps
in the correct order, handling both automatic and interactive processors.
"""

from typing import Dict, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .context import BookfixContext

from .logging import log_message


def get_available_processors() -> Dict[str, str]:
    """
    Get a dictionary of available processors and their descriptions.
    
    Returns:
        Dictionary mapping processor names to descriptions
    """
    return {
        'replacements': 'Automatic text replacements',
        'choices': 'Interactive word choices (homograph disambiguation)', 
        'allcaps': 'All-caps text processing',
        'numbered': 'Numbered line processing',
        'periods': 'Period processing',
        'roman': 'Roman numeral conversion',
        'blanklines': 'Blank line removal',
        'lowercase': 'Convert to lowercase',
        'pagination': 'Page number removal'
    }


def run_processing(
    ctx: 'BookfixContext', 
    enabled_steps: Dict[str, bool],
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    status_callback: Optional[Callable[[str], None]] = None
) -> 'BookfixContext':
    """
    Run the processing pipeline with enabled steps.
    
    Args:
        ctx: BookfixContext containing text and configuration
        enabled_steps: Dictionary of step names and whether they're enabled
        progress_callback: Optional callback for progress updates
        status_callback: Optional callback for status messages
        
    Returns:
        Updated BookfixContext after processing
    """
    log_message("Starting processing pipeline")
    
    if status_callback:
        status_callback("Initializing processing pipeline...")
    
    # Define processing order - interactive steps are handled separately by GUI
    processing_order = [
        'replacements',
        'allcaps', 
        'numbered',
        'periods',
        'roman',
        'blanklines',
        'lowercase',
        'pagination'
    ]
    
    # Filter to only enabled automatic steps
    enabled_auto_steps = []
    interactive_steps = ['choices', 'allcaps', 'numbered']  # These require GUI interaction
    for step in processing_order:
        if enabled_steps.get(step, False):
            # Skip interactive steps - they're handled by GUI
            if step not in interactive_steps:
                enabled_auto_steps.append(step)
    
    total_steps = len(enabled_auto_steps)
    
    if total_steps == 0:
        log_message("No automatic processing steps enabled")
        if status_callback:
            status_callback("No automatic processing steps enabled")
        return ctx
    
    log_message(f"Running {total_steps} automatic processing steps")
    
    # Process each enabled step
    for step_index, step_name in enumerate(enabled_auto_steps):
        
        if progress_callback:
            progress_callback(step_index, total_steps, f"Processing: {step_name}")
            
        if status_callback:
            status_callback(f"Running {step_name}...")
            
        log_message(f"Running processor: {step_name}")
        
        try:
            ctx = _run_processor(step_name, ctx)
            log_message(f"Completed processor: {step_name}")
            
        except Exception as e:
            error_msg = f"Error in {step_name} processor: {str(e)}"
            log_message(error_msg, level="ERROR")
            if status_callback:
                status_callback(f"Error in {step_name}: {str(e)}")
            # Continue with other processors even if one fails
    
    # Final progress update
    if progress_callback:
        progress_callback(total_steps, total_steps, "Automatic processing complete")
        
    if status_callback:
        status_callback("Automatic processing complete")
    
    log_message("run_processing pipeline setup complete.")
    return ctx


def _run_processor(processor_name: str, ctx: 'BookfixContext') -> 'BookfixContext':
    """
    Run a specific processor on the context.
    
    Args:
        processor_name: Name of the processor to run
        ctx: BookfixContext to process
        
    Returns:
        Updated BookfixContext
    """
    if processor_name == 'replacements':
        from .processors.automatic import AutomaticReplacementProcessor
        processor = AutomaticReplacementProcessor()
        return processor.process_replacements(ctx)
        
    elif processor_name == 'allcaps':
        from .processors.allcaps import AllCapsProcessor
        processor = AllCapsProcessor()
        # Note: AllCaps is interactive, handled by GUI
        return ctx
        
    elif processor_name == 'numbered':
        from .processors.numbered import NumberedLineProcessor  
        processor = NumberedLineProcessor()
        # Note: Numbered is interactive, handled by GUI
        return ctx
        
    elif processor_name == 'periods':
        from .processors.periods import PeriodProcessor
        processor = PeriodProcessor()
        return processor.process_periods(ctx)
        
    elif processor_name == 'roman':
        from .processors.roman import RomanNumeralProcessor
        processor = RomanNumeralProcessor()
        return processor.process_roman_numerals(ctx)
        
    elif processor_name == 'blanklines':
        from .processors.blanklines import BlankLineProcessor
        processor = BlankLineProcessor()
        return processor.process_blank_lines(ctx)
        
    elif processor_name == 'lowercase':
        from .processors.lowercase import LowercaseProcessor
        processor = LowercaseProcessor()
        return processor.process_lowercase(ctx)
        
    elif processor_name == 'pagination':
        from .processors.pagination import PaginationProcessor
        processor = PaginationProcessor()
        return processor.process_pagination(ctx)
        
    else:
        log_message(f"Unknown processor: {processor_name}", level="WARNING")
        return ctx