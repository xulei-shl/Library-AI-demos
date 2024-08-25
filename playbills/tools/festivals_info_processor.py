from tools.festivals_info_extractor import get_description
import json

# `演出事件`各个实体的`description` null时，再次LLM提取
def process_item(item, md_file_path, logger):
    def add_description_with_metadata(target, name, key):
        formatted_name = f"{name}（{key}）"
        if 'description' not in target or not target['description'] or target['description'] == "null":
            description_json, token_count, output_token_count = get_description(md_file_path, logger, formatted_name)
            if description_json:
                try:
                    description_data = json.loads(description_json)
                    if description_data.get('description') is not None and description_data.get('description') != "null":
                        target['description'] = description_data.get('description', '')
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON for {formatted_name}: {e}")
            return token_count, output_token_count
        return 0, 0

    total_token_count = 0
    total_output_token_count = 0

    if 'performingEvent' in item and item['performingEvent'] is not None:
        performing_event = item['performingEvent']
        
        # Process name and description
        if 'name' in performing_event:
            token_count, output_token_count = add_description_with_metadata(performing_event, performing_event['name'], 'performingEvent')
            total_token_count += token_count
            total_output_token_count += output_token_count
        
        # Process location
        if 'location' in performing_event and performing_event['location'] is not None:
            location = performing_event['location']
            if 'venue' in location and location['venue']:
                token_count, output_token_count = add_description_with_metadata(location, location['venue'], 'venue')
                total_token_count += token_count
                total_output_token_count += output_token_count
        
        # Process involvedParties
        if 'involvedParties' in performing_event and performing_event['involvedParties'] is not None:
            for party in performing_event['involvedParties']:
                if party is not None and 'name' in party:
                    token_count, output_token_count = add_description_with_metadata(party, party['name'], 'involvedParties')
                    total_token_count += token_count
                    total_output_token_count += output_token_count
        
        # Process performingTroupes
        if 'performingTroupes' in performing_event and performing_event['performingTroupes'] is not None:
            for troupe in performing_event['performingTroupes']:
                if troupe is not None and 'name' in troupe:
                    token_count, output_token_count = add_description_with_metadata(troupe, troupe['name'], 'performingTroupes')
                    total_token_count += token_count
                    total_output_token_count += output_token_count

    return total_token_count, total_output_token_count