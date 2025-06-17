"""Action description"""

from solace_ai_connector.common.log import log


from solace_agent_mesh.common.action import Action
from solace_agent_mesh.common.action_response import ActionResponse

# To import from a local file, like this file, use a relative path from the graph_database
# For example, to load this class, use:
#   from graph_database.actions.sample_action import SampleAction


class SampleAction(Action):
    def __init__(self, **kwargs):
        super().__init__(
            {
                "name": "sample_action",
                "prompt_directive": ("detailed description of the action. " "examples, chain of thought, etc." "details for parameters"),
                "params": [
                    {
                        "name": "sampleParam",
                        "desc": "Description of the parameter",
                        "type": "type of parameter (string, int, etc.)",
                    }
                ],
                "required_scopes": ["graph_database:sample_action:read"],
            },
            **kwargs,
        )

    def invoke(self, params, meta={}) -> ActionResponse:
        log.debug("Doing sample action: %s", params["sampleParam"])
        return self.do_action(params["sampleParam"])

    def do_action(self, sample) -> ActionResponse:
        sample += " Action performed"
        return ActionResponse(message=sample)
