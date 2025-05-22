import unittest
from unittest.mock import patch, MagicMock
import os
import json
import sys

# Add the current directory to sys.path to allow importing translators
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import dialogs_translator
import objects_translator # Import for the new test class

class TestDialogsTranslator(unittest.TestCase):

    def setUp(self):
        self.original_api_key = os.environ.get('GEMINI_API_KEY')
        os.environ['GEMINI_API_KEY'] = 'test_dummy_key_dialogs'
        
        self.dummy_file_path = "test_dialog_for_translation.json"
        self.text_to_translate_lc = "testo da tradurre" # Italian for "text to translate"
        self.mock_translated_text_lc = "translated: testo da tradurre"
        self.expected_final_text_lc = "translated: testo da tradurre"

        dummy_data = {
            "events": [
                {
                    "pages": [{
                        "list": [
                            {"code": 401, "parameters": [self.text_to_translate_lc]}
                        ]
                    }]
                }
            ]
        }
        with open(self.dummy_file_path, 'w', encoding='utf-8') as f:
            json.dump(dummy_data, f)

    def tearDown(self):
        if self.original_api_key is not None:
            os.environ['GEMINI_API_KEY'] = self.original_api_key
        elif 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']
        
        if os.path.exists(self.dummy_file_path):
            os.remove(self.dummy_file_path)

    @patch('dialogs_translator.genai.GenerativeModel')
    @patch('dialogs_translator.genai.configure') # Not strictly needed if model is passed directly
    def test_translate_dialogs_logic_successful_translation(self, mock_genai_configure, mock_genai_generativemodel_constructor):
        mock_model_instance = MagicMock()
        mock_gemini_response = MagicMock()
        mock_gemini_response.text = self.mock_translated_text_lc 
        mock_model_instance.generate_content.return_value = mock_gemini_response
        
        # This mock ensures that if GenerativeModel was called, it returns our instance
        mock_genai_generativemodel_constructor.return_value = mock_model_instance

        translated_data, num_translations = dialogs_translator.translate(
            file_path=self.dummy_file_path,
            model=mock_model_instance,
            src='it',
            dst='en',
            verbose=False,
            max_retries=1
        )

        self.assertEqual(num_translations, 1)
        mock_model_instance.generate_content.assert_called_once_with(
            f"Translate the following text from it to en: {self.text_to_translate_lc}"
        )
        self.assertEqual(
            translated_data["events"][0]["pages"][0]["list"][0]["parameters"][0],
            self.expected_final_text_lc
        )

class TestObjectsTranslator(unittest.TestCase):

    def setUp(self):
        self.original_api_key = os.environ.get('GEMINI_API_KEY')
        os.environ['GEMINI_API_KEY'] = 'test_dummy_key_objects'

        self.dummy_file_path = "test_object_for_translation.json"
        self.name_to_translate = "Oggetto di Prova" # "Test Object"
        self.desc_to_translate = "Questa è una descrizione di prova." # "This is a test description."

        # Expected translations (Gemini might return these)
        self.mock_translated_name = "Translated: Oggetto di Prova"
        self.mock_translated_desc = "Translated: Questa è una descrizione di prova."
        
        # Expected final text after script's case logic
        # objects_translator.py logic for name (neatly=False):
        # if target[0].isalpha() and translation[0].isalpha and not target[0].isupper(): translation = translation[0].lower() + translation[1:]
        # Oggetto di Prova (Cap) -> Translated: Oggetto di Prova (Cap) -> Stays Cap
        self.expected_final_name = "Translated: Oggetto di Prova"

        # objects_translator.py logic for description (neatly=True, but print_neatly is complex to mock here,
        # so we focus on the translation part. The case logic is the same before print_neatly)
        # Questa è una descrizione di prova. (Cap) -> Translated: Questa è una descrizione di prova. (Cap) -> Stays Cap
        self.expected_final_desc = "Translated: Questa è una descrizione di prova."


        # Data structure for a common type of object file (e.g. Items.json, Armors.json)
        dummy_data = [
            {
                "id": 1,
                "name": self.name_to_translate,
                "description": self.desc_to_translate,
                "profile": "" # objects_translator also tries to translate profile if present
            }
        ]
        with open(self.dummy_file_path, 'w', encoding='utf-8') as f:
            json.dump(dummy_data, f)

    def tearDown(self):
        if self.original_api_key is not None:
            os.environ['GEMINI_API_KEY'] = self.original_api_key
        elif 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']

        if os.path.exists(self.dummy_file_path):
            os.remove(self.dummy_file_path)

    @patch('objects_translator.print_neatly') # Mock print_neatly to simplify description check
    @patch('objects_translator.genai.GenerativeModel')
    @patch('objects_translator.genai.configure') # Not strictly needed if model is passed
    def test_translate_objects_successful_translation(self, mock_genai_configure, mock_genai_generativemodel_constructor, mock_print_neatly):
        mock_model_instance = MagicMock()

        # Configure side_effect for multiple calls to generate_content
        # First call for 'name', second for 'description'
        mock_response_name = MagicMock()
        mock_response_name.text = self.mock_translated_name
        
        mock_response_desc = MagicMock()
        mock_response_desc.text = self.mock_translated_desc
        
        mock_model_instance.generate_content.side_effect = [mock_response_name, mock_response_desc]
        
        mock_genai_generativemodel_constructor.return_value = mock_model_instance

        # Mock print_neatly to just return the input text as a single-element list
        # as objects_translator expects a list from print_neatly.
        # For description, it uses text_neat[0] + '\n' + text_neat[1] if len > 1, else text_neat[0]
        # We are testing translation, not print_neatly's formatting here.
        mock_print_neatly.side_effect = lambda text, max_len: [text]


        translated_data, num_translations = objects_translator.translate(
            file_path=self.dummy_file_path,
            model=mock_model_instance,
            src='it',
            dst='en',
            verbose=False,
            max_retries=1,
            max_len=55 # As used in objects_translator
        )

        self.assertEqual(num_translations, 2) # Name and Description

        # Check calls to generate_content
        calls = mock_model_instance.generate_content.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0][0], f"Translate the following text from it to en: {self.name_to_translate}")
        
        
        # Pre-calculate the expected prompt for the description to avoid f-string syntax issues
        processed_desc_for_prompt = self.desc_to_translate.replace('\n', ' ')
        # Construct the expected prompt string using concatenation to avoid f-string parsing issues with special characters
        expected_desc_prompt = "Translate the following text from it to en: " + processed_desc_for_prompt
        self.assertEqual(calls[1][0][0], expected_desc_prompt)

        # Check the translated text
        self.assertEqual(translated_data[0]["name"], self.expected_final_name)
        # The description translation in objects_translator.py undergoes print_neatly.
        # If print_neatly returns a list with one item, it's used directly.
        # If it returns more, it joins them with \n.
        # Since we mocked print_neatly to return [translated_text], this should be straightforward.
        self.assertEqual(translated_data[0]["description"], self.expected_final_desc)
        
        # Assert mock_print_neatly was called for the description
        # The description is passed to translate_and_check with neatly=True
        mock_print_neatly.assert_called_once_with(self.mock_translated_desc, 55)


if __name__ == '__main__':
    unittest.main()
