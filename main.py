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

    def get_ollama_headers(self):
        headers = {}
        if self.preferences["ollama_headers"]:
            for header in self.preferences["ollama_headers"].split(","):
                header_key, header_value = header.split(":")
                headers[header_key.strip()] = header_value.strip()
        return headers

    def list_models(self):
        r = requests.get(
            self.preferences["ollama_host"] + "/api/tags",
            headers=self.get_ollama_headers(),
        )
        response = r.json()

        if r.status_code != 200:
            raise OllamaException("Error connecting to ollama.")

        models = []

        for m in response["models"]:
            if m and m["name"]:
                models.append(m["name"])

        return models

    def generate(self, event):
        logger.info(event)
        
        system_prompt = event.get('system_prompt', self.preferences['ollama_system_prompt'])
        prompt = event['query']
        
        data = {
            "model": event['model'],
            "prompt": prompt,
            "system": system_prompt,
            "stream": False
        }

        r = requests.post(
            self.preferences["ollama_host"] + "/api/generate",
            data=json.dumps(data),
            headers=self.get_ollama_headers(),
        )
        response = r.json()

        if r.status_code != 200:
            raise OllamaException(
                "Error connecting to ollama.")

        logger.debug(response)

        return response

class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        # event is instance of ItemEnterEvent

        query = event.get_data()
        logger.debug(query)
        # do additional actions here...
        response = extension.generate(query)

        logger.debug(response)

        return RenderResultListAction(
            [
                ExtensionResultItem(
                    icon="images/textty.png", name="Press enter to copy.", description=response['response'], on_enter=CopyToClipboardAction(response['response'])
                )
            ]
        )


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        query = event.get_query().replace(extension.preferences["ollama_kw"] + " ", "")

        items = [
            ExtensionResultItem(
                icon="images/textty.png",
                name="Fix Grammar",
                description=f"Fix grammar issues ✅",
                on_enter=ExtensionCustomAction({
                    "query": query, 
                    "model": extension.preferences["ollama_default_model"], 
                    "system_prompt": extension.preferences['ollama_system_prompt'] + " You are a grammar expert. Fix the grammar of the text. IMPORTANT: Only return the fixed text, do not include any other text in your response."
                }, keep_app_open=True),
            ),
            ExtensionResultItem(
                icon="images/textty.png",
                name="More Casual",
                description=f"Make this more conversational 🏖️",
                on_enter=ExtensionCustomAction({
                    "query": query, 
                    "model": extension.preferences["ollama_default_model"], 
                    "system_prompt": "You are a writing style expert. Convert the following text to a more casual, conversational tone. IMPORTANT: Only return the converted text, do not include any other text in your response."
                }, keep_app_open=True),
            ),
            ExtensionResultItem(
                icon="images/textty.png",
                name="More Formal",
                description=f"Make this more professional 👔",
                on_enter=ExtensionCustomAction({
                    "query": query, 
                    "model": extension.preferences["ollama_default_model"], 
                    "system_prompt": "You are a writing style expert. Convert the following text to a more formal, professional tone. IMPORTANT: Only return the converted text, do not include any other text in your response."
                }, keep_app_open=True),
            )
        ]

        return RenderResultListAction(items)


class OllamaException(Exception):
    """Exception thrown when there was an error calling the ollama API"""

    pass


if __name__ == "__main__":
    TexttyExtension().run()
