# Instrucciones para importar flujos en Langflow

## IMPORTANTE: Reimportar todos los flujos después de esta actualización
Los JSONs ahora tienen la API key de Gemini ya configurada en cada nodo.

## Pasos:
1. Abre http://localhost:7860
2. Elimina los flujos existentes (si los tienes importados)
3. Importa cada JSON desde: My Flows → Import
   - Arquitectura_Secuencial.json  → ID: 90305752-6095-472a-af6c-d3914a57d5f8
   - Arquitectura_Jerarquica.json  → ID: 7db32208-bb48-41c1-94f2-e1a7891cd1b6
   - Arquitectura_HumanLoop.json   → ID: e7e08b24-9b29-4743-99d5-3cb9fab2e297
4. Verifica que en cada nodo "Agent" o "Google Generative AI" 
   aparezca la API key configurada
5. Reinicia uvicorn: uvicorn main:app --reload

## Si el ID cambia al importar:
Actualiza el backend/.env con el nuevo ID del flujo.
