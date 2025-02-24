# libraries
from __future__ import annotations

import json
import logging
from typing import Optional, Any, Dict

from colorama import Fore, Style
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate

from ..prompts import generate_subtopics_prompt
from .costs import estimate_llm_cost
from .validators import Subtopics


def get_llm(llm_provider, **kwargs):
    from gpt_researcher.llm_provider import GenericLLMProvider
    return GenericLLMProvider.from_provider(llm_provider, **kwargs)


async def create_chat_completion(
        messages: list,  # type: ignore
        model: Optional[str] = None,
        temperature: Optional[float] = 0.4,
        max_tokens: Optional[int] = 4000,
        llm_provider: Optional[str] = None,
        stream: Optional[bool] = False,
        websocket: Any | None = None,
        llm_kwargs: Dict[str, Any] | None = None,
        cost_callback: callable = None,
        reasoning_effort: Optional[str] = "low"
) -> str:
    """Create a chat completion using the OpenAI API
    Args:
        messages (list[dict[str, str]]): The messages to send to the chat completion
        model (str, optional): The model to use. Defaults to None.
        temperature (float, optional): The temperature to use. Defaults to 0.4.
        max_tokens (int, optional): The max tokens to use. Defaults to 4000.
        stream (bool, optional): Whether to stream the response. Defaults to False.
        llm_provider (str, optional): The LLM Provider to use.
        webocket (WebSocket): The websocket used in the currect request,
        cost_callback: Callback function for updating cost
    Returns:
        str: The response from the chat completion
    """
    # validate input
    if model is None:
        raise ValueError("Model cannot be None")
    if max_tokens is not None and max_tokens > 16001:
        raise ValueError(
            f"Max tokens cannot be more than 16,000, but got {max_tokens}")

    # Get the provider from supported providers
    kwargs = {
        'model': model,
        **(llm_kwargs or {})
    }

    if 'o3' in model or 'o1' in model:
        kwargs['reasoning_effort'] = reasoning_effort
    else:
        kwargs['temperature'] = temperature
        kwargs['max_tokens'] = max_tokens

    provider = get_llm(llm_provider, **kwargs)
    response = ""
    # create response
    for _ in range(10):  # maximum of 10 attempts
        response = await provider.get_chat_response(
            messages, stream, websocket
        )

        if cost_callback:
            llm_costs = estimate_llm_cost(str(messages), response)
            cost_callback(llm_costs)

        return response

    logging.error(f"Failed to get response from {llm_provider} API")
    raise RuntimeError(f"Failed to get response from {llm_provider} API")


async def construct_subtopics(task: str, data: str, config, subtopics: list = []) -> list:
    """
    Construct subtopics based on the given task and data.

    Args:
        task (str): The main task or topic.
        data (str): Additional data for context.
        config: Configuration settings.
        subtopics (list, optional): Existing subtopics. Defaults to [].

    Returns:
        list: A list of constructed subtopics.
    """
    try:
        parser = PydanticOutputParser(pydantic_object=Subtopics)

        prompt = PromptTemplate(
            template=generate_subtopics_prompt(),
            input_variables=["task", "data", "subtopics", "max_subtopics"],
            partial_variables={
                "format_instructions": parser.get_format_instructions()},
        )

        kwargs = {
            'model': config.smart_llm_model,
            **(config.llm_kwargs or {})
        }

        temperature = config.temperature
        if 'o3' in config.smart_llm_model or 'o1' in config.smart_llm_model:
            kwargs['reasoning_effort'] = "high"
        else:
            kwargs['temperature'] = config.temperature
            kwargs['max_tokens'] = config.smart_token_limit

        provider = get_llm(config.smart_llm_provider, **kwargs)

        model = provider.llm

        chain = prompt | model | parser

        output = chain.invoke({
            "task": task,
            "data": data,
            "subtopics": subtopics,
            "max_subtopics": config.max_subtopics
        })

        return output

    except Exception as e:
        print("Exception in parsing subtopics : ", e)
        return subtopics
