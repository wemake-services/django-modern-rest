import msgspec

def yaml_dumps(schema: object) -> str:
    """Serialize schema to a decoded YAML string."""
    return msgspec.yaml.encode(schema).decode('utf-8')
