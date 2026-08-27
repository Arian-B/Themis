"""
tools/pii/redactor.py — PII Redaction using Microsoft Presidio.
"""
import logging

logger = logging.getLogger(__name__)

# Initialize engines globally so they are only loaded once.
# presidio requires the spacy model 'en_core_web_lg' to be downloaded.
_analyzer = None
_anonymizer = None

def _get_engines():
    global _analyzer, _anonymizer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine

        logger.info("Initializing Presidio Analyzer...")
        _analyzer = AnalyzerEngine()
    if _anonymizer is None:
        from presidio_anonymizer import AnonymizerEngine

        logger.info("Initializing Presidio Anonymizer...")
        _anonymizer = AnonymizerEngine()
    return _analyzer, _anonymizer

def redact_pii(text: str) -> str:
    """
    Detects and redacts PII (names, emails, phone numbers, addresses, etc.)
    from the given text using Presidio.
    """
    if not text:
        return text
        
    try:
        analyzer, anonymizer = _get_engines()
        
        # Analyze text for PII
        # 'en' defaults to the installed spacy model
        results = analyzer.analyze(text=text, entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION"], language="en")
        
        # Anonymize the findings (replaces with e.g. <PERSON>)
        anonymized = anonymizer.anonymize(text=text, analyzer_results=results)
        
        return anonymized.text
    except Exception as e:
        logger.error(f"PII redaction failed: {e}. Falling back to unredacted text.")
        return text
