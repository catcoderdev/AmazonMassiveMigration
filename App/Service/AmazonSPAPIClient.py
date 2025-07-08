import requests
from datetime import datetime, timedelta
from typing import List, Optional
import time


class AmazonSPAPIClient:
    def __init__(self, access_token: str, marketplace_id: str = "A1AM78C64UM0Y8", region: str = "na"):
        """
        Inicializa el cliente para Amazon SP-API

        Args:
            access_token: Token de acceso LWA (Login with Amazon)
            marketplace_id: ID del marketplace (default: "A1AM78C64UM0Y8" para México)
            region: Región del endpoint (na, eu, fe)
        """
        self.access_token = access_token
        self.marketplace_id = marketplace_id

        # URLs base por región
        base_urls = {
            "na": "https://sellingpartnerapi-na.amazon.com",
            "eu": "https://sellingpartnerapi-eu.amazon.com",
            "fe": "https://sellingpartnerapi-fe.amazon.com"
        }

        self.base_url = base_urls.get(region, base_urls["na"])
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'x-amz-access-token': access_token
        }

    def get_order_ids_last_year(self) -> List[str]:
        """
        Obtiene todos los IDs de órdenes del último año (desde hoy hasta 365 días atrás)

        Returns:
            List[str]: Lista con todos los Amazon Order IDs
        """
        # Calcular fechas (último año) - SP-API requiere formato ISO 8601
        end_date = datetime.now() - timedelta(hours=5)
        start_date = end_date - timedelta(days=(365 * 2))

        # Formatear en ISO 8601 con timezone UTC
        created_after = start_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        created_before = end_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        return self._get_orders_in_range(created_after, created_before)

    def get_order_ids_custom_range(self, start_date: str, end_date: str) -> List[str]:
        """
        Obtiene IDs de órdenes en un rango de fechas personalizado

        Args:
            start_date: Fecha inicio en formato 'YYYY-MM-DD' o ISO 8601
            end_date: Fecha fin en formato 'YYYY-MM-DD' o ISO 8601

        Returns:
            List[str]: Lista con todos los Amazon Order IDs
        """
        # Convertir a formato ISO 8601 si es necesario
        if 'T' not in start_date:
            start_date = f"{start_date}T00:00:00.000Z"
        if 'T' not in end_date:
            end_date = f"{end_date}T23:59:59.000Z"

        return self._get_orders_in_range(start_date, end_date)

    def _get_orders_in_range(self, created_after: str, created_before: str) -> List[str]:
        """
        Método interno para obtener órdenes en un rango específico

        Args:
            created_after: Fecha inicio en formato ISO 8601
            created_before: Fecha fin en formato ISO 8601

        Returns:
            List[str]: Lista de Amazon Order IDs
        """
        all_order_ids = []
        next_token = None
        page = 1

        print(f"Obteniendo órdenes Amazon desde {created_after} hasta {created_before}")

        while True:
            try:
                # Parámetros para SP-API
                params = {
                    'MarketplaceIds': self.marketplace_id,
                    'CreatedAfter': created_after,
                    'CreatedBefore': created_before,
                    'MaxResultsPerPage': 100  # Máximo permitido por SP-API
                }

                # Agregar NextToken si existe (para paginación)
                if next_token:
                    params['NextToken'] = next_token

                # Hacer petición al endpoint de órdenes
                url = f"{self.base_url}/orders/v0/orders"
                response = requests.get(url, headers=self.headers, params=params)

                # Verificar respuesta
                if response.status_code != 200:
                    print(f"Error en página {page}: {response.status_code} - {response.text}")
                    break

                data = response.json()

                # Verificar si hay errores en la respuesta
                if 'errors' in data:
                    print(f"Errores en la respuesta: {data['errors']}")
                    break

                # Extraer órdenes del payload
                payload = data.get('payload', {})
                orders = payload.get('Orders', [])

                if not orders:
                    print(f"No hay más órdenes en página {page}")
                    break

                # Extraer Amazon Order IDs
                page_order_ids = [order.get('AmazonOrderId') for order in orders
                                  if order.get('AmazonOrderId')]
                all_order_ids.extend(page_order_ids)

                print(f"Página {page}: {len(page_order_ids)} órdenes obtenidas")

                # Verificar si hay más páginas con NextToken
                next_token = payload.get('NextToken')
                if not next_token:
                    print("No hay más páginas (sin NextToken)")
                    break

                page += 1

                # Pausa para respetar rate limits de Amazon (máx 10 req/seg)
                time.sleep(0.2)

            except requests.RequestException as e:
                print(f"Error de conexión en página {page}: {e}")
                break
            except Exception as e:
                print(f"Error inesperado en página {page}: {e}")
                break

        print(f"Total de órdenes obtenidas: {len(all_order_ids)}")
        return all_order_ids

    def get_order_details(self, order_id: str) -> dict:
        """
        Obtiene detalles de una orden específica

        Args:
            order_id: Amazon Order ID

        Returns:
            dict: Detalles de la orden
        """
        try:
            url = f"{self.base_url}/orders/v0/orders/{order_id}"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error obteniendo orden {order_id}: {response.status_code}")
                return {}

        except Exception as e:
            print(f"Error obteniendo detalles de {order_id}: {e}")
            return {}

    def start(self, access_token: str, seller_id: str):
        """
        Método principal que obtiene todos los IDs de órdenes del último año
        y los envía al endpoint de normalización

        Args:
            access_token: Token de acceso LWA de Amazon
            seller_id: ID del seller para el endpoint de normalización
        """
        # Actualizar token si es diferente
        if access_token != self.access_token:
            self.access_token = access_token
            self.headers['Authorization'] = f'Bearer {access_token}'
            self.headers['x-amz-access-token'] = access_token

        # Obtener IDs del último año
        print("Obteniendo IDs de órdenes del último año desde Amazon SP-API...")
        order_ids = self.get_order_ids_last_year()

        print(f"Total de órdenes obtenidas: {len(order_ids)}")

        if not order_ids:
            print("❌ No se encontraron órdenes para procesar")
            return

        # Configuración para normalización
        normalize_url = "https://integraciones.infrastructure-t1.com/amazon/orders/normalize"

        # Procesar cada orden
        print(f"\nIniciando normalización de {len(order_ids)} órdenes...")

        successful_orders = 0
        failed_orders = 0

        for i, order_id in enumerate(order_ids, 1):
            try:
                # Payload para el POST
                payload = {
                    "seller_id": str(seller_id),
                    "order_id": order_id
                }

                # Headers para normalización
                headers = {
                    'Content-Type': 'application/json'
                }

                # Hacer POST request
                time.sleep(0.5)
                response = requests.post(normalize_url, json=payload, headers=headers)

                if response.status_code == 200:
                    successful_orders += 1
                    print(f"✅ {i}/{len(order_ids)} - Orden {order_id} normalizada exitosamente")
                else:
                    failed_orders += 1
                    print(
                        f"❌ {i}/{len(order_ids)} - Error en orden {order_id}: {response.status_code} - {response.text}")

                # Pausa pequeña para no sobrecargar el servidor
                time.sleep(0.1)

                # Mostrar progreso cada 50 órdenes
                if i % 50 == 0:
                    print(f"📊 Progreso: {i}/{len(order_ids)} órdenes procesadas")
                    print(f"   ✅ Exitosas: {successful_orders} | ❌ Errores: {failed_orders}")

            except requests.RequestException as e:
                failed_orders += 1
                print(f"❌ {i}/{len(order_ids)} - Error de conexión en orden {order_id}: {e}")
            except Exception as e:
                failed_orders += 1
                print(f"❌ {i}/{len(order_ids)} - Error inesperado en orden {order_id}: {e}")

        # Resumen final
        print(f"\n🎯 RESUMEN FINAL:")
        print(f"✅ Órdenes normalizadas exitosamente: {successful_orders}")
        print(f"❌ Órdenes con errores: {failed_orders}")
        print(f"📊 Total procesadas: {len(order_ids)}")
        print(f"📈 Tasa de éxito: {(successful_orders / len(order_ids) * 100):.1f}%")


# Ejemplo de uso:
if __name__ == "__main__":
    # Crear cliente para México
    client = AmazonSPAPIClient(
        access_token="dummy_token",  # Se actualizará en start()
        marketplace_id="A1AM78C64UM0Y8"  # México
    )

    # Ejecutar proceso completo
    client.start(
        access_token="TU_AMAZON_ACCESS_TOKEN",  # Tu token real de Amazon
        seller_id="TU_SELLER_ID"  # Tu seller ID real
    )