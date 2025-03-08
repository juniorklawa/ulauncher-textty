import json
import logging
import requests

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction


logger = logging.getLogger(__name__)


class TexttyExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

    def generate(self, event):
        logger.info(event)
        
        base_system_prompt = self.preferences['default_prompt']
        
        custom_system_prompt = event.get('system_prompt', '')
        
        if custom_system_prompt:
            system_prompt = f"{base_system_prompt} {custom_system_prompt}"
        else:
            system_prompt = base_system_prompt
        
        prompt = event['query']
        model = event.get('model', self.preferences['default_model'])
        
        if self.preferences['ai_provider'] == 'ollama':
            return self._generate_ollama(prompt, system_prompt, model)
        elif self.preferences['ai_provider'] == 'openai':
            return self._generate_openai(prompt, system_prompt, model)
        else:
            raise TexttyException(f"Unknown AI provider: {self.preferences['ai_provider']}")

    def _generate_ollama(self, prompt, system_prompt, model):
        data = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False
        }

        r = requests.post(
            self.preferences["ollama_host"] + "/api/generate",
            data=json.dumps(data)
        )
        
        if r.status_code != 200:
            raise TexttyException("Error connecting to ollama.")
            
        response = r.json()
        logger.debug(response)
        
        return {"response": response['response']}

    def _generate_openai(self, prompt, system_prompt, model):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.preferences['openai_api_key']}"
        }
        
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }
        
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            data=json.dumps(data)
        )
        
        if r.status_code != 200:
            raise TexttyException("Error connecting to OpenAI API.")
            
        response = r.json()
        logger.debug(response)
        
        return {"response": response['choices'][0]['message']['content']}


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        query = event.get_data()
        logger.debug(query)
        response = extension.generate(query)

        logger.debug(response)
        
        ai_answer = response['response']
        
        try:
            wrap_length = int(extension.preferences["wrap_length"])
        except ValueError:
            wrap_length = 80
            
        wrapped_lines = []
        current_line = ""
        for word in ai_answer.split():
            if len(current_line + word) <= wrap_length:
                current_line += " " + word
            else:
                wrapped_lines.append(current_line.strip())
                current_line = word
        wrapped_lines.append(current_line.strip())

        wrapped_answer = "\n".join(wrapped_lines)

        return RenderResultListAction(
            [
                ExtensionResultItem(
                    icon="images/textty.png", 
                    name="Textty:", 
                    description=wrapped_answer, 
                    on_enter=CopyToClipboardAction(ai_answer)
                )
            ]
        )


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        query = event.get_query().replace(extension.preferences["textty_kw"] + " ", "")

        items = [
            ExtensionResultItem(
                icon="images/textty.png",
                name="Fix Grammar",
                description=f"Fix grammar ✅",
                on_enter=ExtensionCustomAction({
                    "query": f"You are a grammar expert. Fix the grammar of the text. Keep the same tone, style, and structure of the text. IMPORTANT: Only return the fixed text, do not include any other text in your response. Here's the text to fix: {query}", 
                    "model": extension.preferences["default_model"], 
                }, keep_app_open=True),
            ),
            ExtensionResultItem(
                icon="images/textty.png",
                name="More Casual",
                description=f"Make this more conversational 🏖️",
                on_enter=ExtensionCustomAction({
                    "query": f"You are a writing style expert. Convert the following text to a more casual, conversational tone. IMPORTANT: Only return the converted text, do not include any other text in your response. Here's the text to convert: {query}", 
                    "model": extension.preferences["default_model"], 
                }, keep_app_open=True),
            ),
            ExtensionResultItem(
                icon="images/textty.png",
                name="More Formal",
                description=f"Make this more professional 👔",
                on_enter=ExtensionCustomAction({
                    "query": f"You are a writing style expert. Convert the following text to a more formal, professional tone. IMPORTANT: Only return the converted text, do not include any other text in your response. Here's the text to convert: {query}", 
                    "model": extension.preferences["default_model"], 
                }, keep_app_open=True),
            )
        ]

        return RenderResultListAction(items)


class TexttyException(Exception):
    pass


if __name__ == "__main__":
    TexttyExtension().run()
