import argparse
import json
import os
import time
import sys # For sys.exit

import google.generativeai as genai # Replaced googletrans
# from googletrans import Translator  # pip install googletrans==4.0.0rc1 # Removed

from print_neatly import print_neatly


def translate(file_path, model, src='it', dst='en', verbose=False, max_retries=5, max_len=55): # tr replaced with model

    def translate_sentence_internal(text_to_translate): # Renamed to avoid conflict, text to text_to_translate
        target = text_to_translate
        # translation = tr.translate(target, src=src, dest=dst).text # Old googletrans call
        prompt = f"Translate the following text from {src} to {dst}: {target}"
        translation_result = None
        success_status = False
        try:
            response = model.generate_content(prompt)
            translation_result = response.text
            success_status = True # Assume success if API call returns
        except Exception as e:
            print(f"Error during Gemini API call: {e}")
            # Fall through, translation_result remains None, success_status remains False

        if success_status and target and translation_result and target[0].isalpha() and translation_result[0].isalpha() and not target[0].isupper():
            translation_result = translation_result[0].lower() + translation_result[1:]
        
        if verbose and success_status: # Only print if verbose and successful
            print(target, '->', translation_result)
        return translation_result, success_status # Return text and success status

    def translate_and_check(text_to_check, remove_escape=True, neatly=False, keep_space=True): # Renamed text
        translated_text = None # text_tr renamed
        translation_successful = False # Added to track success
        original_text_for_anomaly = text_to_check # Keep original for error message

        if remove_escape:
            text_to_check = text_to_check.replace('\n', ' ')
        
        try:
            # translate_sentence_internal now returns (text, success_boolean)
            translated_text, translation_successful = translate_sentence_internal(text_to_check)
        except Exception as e_outer: # Catch potential errors from the API call itself if not handled inside
            print(f"Outer exception in translate_and_check: {e_outer}")
        
        if not translation_successful: # If initial attempt failed, try retries
            for i in range(max_retries):
                try:
                    time.sleep(1)
                    translated_text, translation_successful = translate_sentence_internal(text_to_check)
                    if translation_successful: # Break if successful
                        break
                except Exception as e_inner:
                    print(f"Inner exception in translate_and_check on retry {i+1}: {e_inner}")
                    pass
        
        if not translation_successful or translated_text is None:
            print('Anomaly: {}'.format(original_text_for_anomaly))
            return None, 0 # Return original text and 0 for failure count
            
        if neatly:
            try:
                text_neat = print_neatly(translated_text, max_len)
                if len(text_neat) > 1:
                    translated_text = text_neat[0] + '\n' + text_neat[1] # text_tr renamed
                else:
                    translated_text = text_neat[0] # text_tr renamed
            except:
                pass # translated_text remains as is
        if keep_space:
            # text was the original input to translate_and_check, now text_to_check (after replace) or original_text_for_anomaly (before replace)
            # Use original_text_for_anomaly to check the first char, as text_to_check might have had \n replaced
            if original_text_for_anomaly and original_text_for_anomaly[0] == ' ' and translated_text and translated_text[0] != ' ':
                translated_text = ' ' + translated_text # text_tr renamed
        return translated_text, 1 # text_tr renamed

    def translate_based_on_keys(dict_or_list, keys, translations_count=0, remove_escape=True, neatly=False, array_translate=False): # translations renamed
        if isinstance(dict_or_list, dict):
            # Iterate over a copy of keys if modifying the dict during iteration, though here we modify values.
            # Direct iteration should be fine for value modification.
            for d_key in list(dict_or_list.keys()): # Use list() for safety if keys could change, though not expected here
                if isinstance(dict_or_list[d_key], dict) or isinstance(dict_or_list[d_key], list):
                    translations_count = translate_based_on_keys(dict_or_list[d_key], keys, translations_count, remove_escape, neatly, array_translate) # Pass translations_count
                elif d_key in keys and dict_or_list[d_key] and isinstance(dict_or_list[d_key], str) and len(dict_or_list[d_key]) > 0: # Added check for string type and non-empty
                    tr_text, success_inc = translate_and_check(dict_or_list[d_key], remove_escape, neatly) # tr renamed, success renamed
                    if tr_text is not None : # Only assign if translation was successful or returned original
                        dict_or_list[d_key] = tr_text
                    translations_count += success_inc # success renamed
        elif isinstance(dict_or_list, list):
            for i in range(len(dict_or_list)):
                if isinstance(dict_or_list[i], dict) or isinstance(dict_or_list[i], list):
                    translations_count = translate_based_on_keys(dict_or_list[i], keys, translations_count, remove_escape, neatly, array_translate) # Pass translations_count
                elif array_translate and isinstance(dict_or_list[i], str) and len(dict_or_list[i]) > 0:
                    tr_text, success_inc = translate_and_check(dict_or_list[i], remove_escape, neatly) # tr renamed, success renamed
                    if tr_text is not None: # Only assign if translation was successful or returned original
                        dict_or_list[i] = tr_text
                    translations_count += success_inc # success renamed
        return translations_count # Return the accumulated count
    
    # Initialize translations count for this file
    current_file_translations = 0

    with open(file_path, 'r', encoding='utf-8-sig') as datafile:
        data = json.load(datafile)
    num_ids = len([e for e in data if e is not None])
    i = 0

    if file_path.endswith('GalleryList.json'):
        current_file_translations = translate_based_on_keys(data, ['displayName', 'hint', 'stageText', 'sceneText', 'text'], 0) # Pass initial translations=0
    
    elif file_path.endswith('RubiList.json'):
        current_file_translations = translate_based_on_keys(data, [], 0, array_translate=True) # Pass initial translations=0

    else:
        for d_item in data: # d renamed to d_item to avoid conflict with d_key
            if d_item is not None:
                print('{}: {}/{}'.format(file_path, i+1, num_ids))
                i += 1
                if 'name' in d_item.keys() and d_item['name'] and isinstance(d_item['name'], str) and len(d_item['name']) > 0:
                    name_tr, success = translate_and_check(d_item['name'], remove_escape=True, neatly=False)
                    if name_tr is not None: d_item['name'] = name_tr
                    current_file_translations += success
                if 'description' in d_item.keys() and d_item['description'] and isinstance(d_item['description'], str) and len(d_item['description']) > 0:
                    desc_tr, success = translate_and_check(d_item['description'], remove_escape=True, neatly=True)
                    if desc_tr is not None: d_item['description'] = desc_tr
                    current_file_translations += success
                if 'profile' in d_item.keys() and d_item['profile'] and isinstance(d_item['profile'], str) and len(d_item['profile']) > 0:
                    prf_tr, success = translate_and_check(d_item['profile'], remove_escape=True, neatly=True)
                    if prf_tr is not None: d_item['profile'] = prf_tr
                    current_file_translations += success
                for m_idx in range(1, 5): # m renamed to m_idx
                    message_key = 'message' + str(m_idx) # message renamed to message_key
                    if message_key in d_item.keys() and d_item[message_key] and isinstance(d_item[message_key], str) and len(d_item[message_key]) > 0:
                        message_tr, success = translate_and_check(d_item[message_key], remove_escape=False, neatly=False)
                        if message_tr is not None: d_item[message_key] = message_tr
                        current_file_translations += success

    return data, current_file_translations # Return accumulated translations for this file


# usage: python objects_translator.py --source_lang it --dest_lang en
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input_folder", type=str, default="objects")
    ap.add_argument("-sl", "--source_lang", type=str, default="it")
    ap.add_argument("-dl", "--dest_lang", type=str, default="en")
    ap.add_argument("-v", "--verbose", action="store_true", default=False)
    ap.add_argument("-nf", "--no_format", action="store_true", default=False)
    ap.add_argument("-ml", "--max_len", type=int, default=55)
    ap.add_argument("-mr", "--max_retries", type=int, default=10)
    args = ap.parse_args()

    # --- Gemini API Key Configuration ---
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        sys.exit(1) # Exit if key is not found
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro') # Initialize the model once
    except Exception as e:
        print(f"Error configuring Gemini API or model: {e}")
        sys.exit(1)
    # --- End Gemini API Key Configuration ---

    dest_folder = args.input_folder + '_' + args.dest_lang
    total_translations = 0 # Renamed translations to total_translations
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    for file_name in os.listdir(args.input_folder): # file renamed to file_name
        file_path = os.path.join(args.input_folder, file_name)
        if os.path.isfile(os.path.join(dest_folder, file_name)):
            print('skipped file {} because it has already been translated'.format(file_path))
            continue
        if file_name.endswith('.json'):
            print('translating file: {}'.format(file_path))
            # Pass model instead of tr=Translator()
            new_data, t_count = translate(file_path, model=model, max_len=args.max_len, # t renamed to t_count
                                    src=args.source_lang, dst=args.dest_lang, verbose=args.verbose,
                                    max_retries=args.max_retries)
            total_translations += t_count # t renamed to t_count
            new_file = os.path.join(dest_folder, file_name)
            with open(new_file, 'w', encoding='utf-8') as f:
                if not args.no_format:
                    json.dump(new_data, f, indent=4, ensure_ascii=False)
                else:
                    json.dump(new_data, f, ensure_ascii=False)
    print('\ndone! translated in total {} strings'.format(total_translations)) # translations renamed to total_translations
