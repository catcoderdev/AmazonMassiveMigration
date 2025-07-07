import json

from App.Service.AmazonSPAPIClient import AmazonSPAPIClient


def lambda_handler(event, context):
    """
    Lambda handler que procesa mensajes SQS para migración masiva de órdenes Amazon

    Formato esperado del mensaje SQS:
    {
        "access_token": "Atza|IwEBI...",
        "seller_id": "12028"
    }
    """

    try:
        # Validar que hay records en el evento
        if 'Records' not in event or not event['Records']:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No SQS records found in event"})
            }

        # Procesar cada record del SQS (normalmente es uno solo)
        for record in event['Records']:
            try:
                # Parsear el body del mensaje SQS
                message_body = json.loads(record['body'])

                # Extraer access_token y seller_id
                access_token = message_body.get('access_token')
                seller_id = message_body.get('seller_id')

                # Validar que están presentes
                if not access_token:
                    print(f"❌ Error: access_token no encontrado en el mensaje")
                    continue

                if not seller_id:
                    print(f"❌ Error: seller_id no encontrado en el mensaje")
                    continue

                print(f"🚀 Iniciando migración masiva para seller_id: {seller_id}")
                print(f"📝 Token recibido: {access_token[:20]}...")  # Solo primeros 20 chars por seguridad

                # Crear cliente Amazon SP-API
                massiveMigration = AmazonSPAPIClient(
                    access_token="dummy_token",  # Se actualizará en start()
                    marketplace_id="A1AM78C64UM0Y8"  # México
                )

                # Ejecutar migración masiva
                massiveMigration.start(
                    access_token=access_token,
                    seller_id=seller_id
                )

                print(f"✅ Migración completada para seller_id: {seller_id}")

            except json.JSONDecodeError as e:
                print(f"❌ Error parsing JSON del mensaje SQS: {e}")
                print(f"Body problemático: {record.get('body', 'N/A')}")
                continue

            except KeyError as e:
                print(f"❌ Campo faltante en mensaje SQS: {e}")
                continue

            except Exception as e:
                print(f"❌ Error procesando record: {e}")
                continue

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Migración masiva completada exitosamente"})
        }

    except Exception as e:
        print(f"❌ Error general en lambda_handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error interno: {str(e)}"})
        }


# Ejemplo de mensaje SQS esperado:
"""
{
  "Records": [
    {
      "messageId": "12345678-1234-1234-1234-123456789012",
      "body": "{\"access_token\": \"Atza|IwEBI...\", \"seller_id\": \"12028\"}",
      "attributes": {},
      "messageAttributes": {},
      "md5OfBody": "...",
      "eventSource": "aws:sqs",
      "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:MyQueue",
      "awsRegion": "us-east-1"
    }
  ]
}
"""