# =============================================================================
# PATRON: SINGLETON (Creacional)
# =============================================================================
# QUÉ ES:
#   Garantiza que una clase tenga UNA SOLA instancia y proporciona un punto
#   de acceso global a ella. Es el patrón creacional más simple.
#
# POR QUÉ SE USA AQUÍ:
#   En AWS Lambda, cada invocación puede reutilizar el mismo contenedor
#   ("warm start"). Crear un cliente DynamoDB o SNS en cada invocación es
#   costoso e innecesario. El Singleton garantiza que:
#     - El cliente AWS SDK se inicializa UNA VEZ por contenedor Lambda.
#     - Invocaciones subsecuentes reutilizan la conexión existente.
#     - Se ahorra tiempo de cold start y recursos.
#
# CUÁNDO USARLO EN PRODUCCIÓN:
#   - Clientes de base de datos (connection pools)
#   - Clientes de APIs externas (HTTP clients)
#   - Loggers centralizados
#   - Cachés en memoria
#   - Configuración de la aplicación (cargada una vez)
#
# CUÁNDO NO USARLO:
#   - Cuando necesitas múltiples instancias con diferente estado
#   - En tests unitarios (dificulta el mocking si no se diseña bien)
#   - Cuando el recurso es barato de crear y no hay beneficio en reutilizar
# =============================================================================

import os
import boto3


class DynamoDBClient:
    """
    Singleton para el cliente de DynamoDB.

    Garantiza una única instancia del cliente por contenedor Lambda.
    Usa el patrón clásico con __new__ para controlar la instanciación.

    Uso:
        db = DynamoDBClient()
        table = db.table("lab-ms-customers")
        table.get_item(Key={"id": customer_id})
    """

    _instance = None
    _resource = None

    def __new__(cls):
        # __new__ se ejecuta ANTES de __init__.
        # Si ya existe una instancia, la retorna sin crear otra.
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Inicializar el recurso DynamoDB UNA SOLA VEZ
            cls._resource = boto3.resource(
                "dynamodb",
                region_name=os.environ.get("AWS_REGION", "us-east-2"),
            )
        return cls._instance

    def table(self, table_name: str):
        """Retorna una referencia a una tabla DynamoDB."""
        return self._resource.Table(table_name)

    @property
    def resource(self):
        """Acceso directo al recurso boto3 (para operaciones avanzadas)."""
        return self._resource


class SNSClient:
    """
    Singleton para el cliente de SNS (Simple Notification Service).

    Mismo patrón: una instancia por contenedor Lambda.
    Se usa para publicar eventos de dominio al topic SNS.
    """

    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._client = boto3.client(
                "sns",
                region_name=os.environ.get("AWS_REGION", "us-east-2"),
            )
        return cls._instance

    @property
    def client(self):
        return self._client

    def publish(self, topic_arn: str, message: str, message_attributes: dict = None):
        """Publica un mensaje al topic SNS."""
        params = {
            "TopicArn": topic_arn,
            "Message": message,
        }
        if message_attributes:
            params["MessageAttributes"] = message_attributes
        return self._client.publish(**params)


class SQSClient:
    """
    Singleton para el cliente de SQS.
    """

    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._client = boto3.client(
                "sqs",
                region_name=os.environ.get("AWS_REGION", "us-east-2"),
            )
        return cls._instance

    @property
    def client(self):
        return self._client
