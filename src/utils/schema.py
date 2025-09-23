from pydantic import ValidationError


async def verify_schema(packet, schema):
    validated = False
    validation_err_message = None
    validated_packet = None
    
    try:
        validated_packet = schema(**packet)
        validated = True
    except ValidationError as validation_error:
        error_details = validation_error.errors()[0]
        field_name = error_details['loc'][0]
        error_message = error_details['msg']
        validated = False
        validation_err_message = f"Error in field '{field_name}': {error_message}"

    return validated, validation_err_message, validated_packet