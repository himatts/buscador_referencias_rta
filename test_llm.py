"""
Script de prueba para el formateo de referencias usando el LLM
"""

from utils.llm_manager import LLMManager
import logging

# Configurar logging para ver los resultados
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_reference_formatting():
    """Prueba el formateo de referencias usando el LLM"""
    try:
        # Inicializar el LLM Manager
        llm = LLMManager()
        
        # Casos de prueba
        test_cases = [
            {
                "code": "CDB",
                "number": "9493",
                "description": "CLOSET BARILOCHE ECO 150 DUNA-BLANCO mas BLANCO MARQUEZ (1C)"
            },
            {
                "code": "MBT",
                "number": "11306",
                "description": "MUEBLE SUPERIOR COCINA BALBOA BARDOLINO mas TAUPE 71,5X210X34 CM (2C)"
            }
        ]
        
        # Probar cada caso
        for case in test_cases:
            logger.info(f"\nProbando referencia:")
            logger.info(f"Entrada: {case['code']} {case['number']} - {case['description']}")
            
            formatted = llm.format_reference_name(
                code=case['code'],
                number=case['number'],
                description=case['description']
            )
            
            logger.info(f"Resultado: {formatted}")
            
    except Exception as e:
        logger.error(f"Error durante la prueba: {str(e)}")

if __name__ == "__main__":
    test_reference_formatting() 