"""One bounded model correction, preserving original prompt and exact diagnostics."""
import json
import re
from pydantic import ValidationError


class DesignFailure(ValueError):
    code = 'DESIGN_INVALID'
    def __init__(self, attempts):
        self.attempts = attempts
        super().__init__('The design could not satisfy the requested mechanics after one correction. Inspect design_validation.json for fields and constraints.')


def decode(text):
    return json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip()))


def validated_response(provider, system, prompt, first, contract, prepare=lambda x: x):
    attempts=[]
    result=first
    for attempt in range(2):
        raw=None
        try:
            raw=decode(result.text)
            if not isinstance(raw,dict):raise ValueError('Expected one JSON object matching the contract, not an array or scalar')
            value=contract.model_validate(prepare(raw))
            attempts.append({'attempt':attempt+1,'valid':True,'model':result.model})
            return value, attempts
        except (ValidationError, ValueError, TypeError) as exc:
            errors=exc.errors(include_url=False, include_context=False, include_input=False) if isinstance(exc,ValidationError) else [{'loc':[], 'msg':str(exc)[:500]}]
            attempts.append({'attempt':attempt+1,'valid':False,'model':result.model,'errors':errors,'candidate':raw})
            if attempt:
                raise DesignFailure(attempts) from exc
            # The user's original request remains an unchanged prefix. No fallback family.
            result=provider.complete(system,prompt+'\nCorrect only the invalid design fields. Preserve the original controls, exclusions and gameplay. Previous JSON:\n'+result.text+'\nValidation errors:\n'+json.dumps(errors))
