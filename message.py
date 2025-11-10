from sequence.entanglement_management.generation.generation_message import EntanglementGenerationMessage, GenerationMsgType


class HetEntanglementGenerationMessage(EntanglementGenerationMessage):

    def __init__(self, msg_type: GenerationMsgType, receiver: str | None, protocol_type: str, **kwargs):
        super().__init__(msg_type, receiver, protocol_type, **kwargs)

        # need to just add min time
        self.min_time: int | None = None

        if ('click_type' in kwargs):
            self.click_type = kwargs['click_type']
        else:
            self.click_type = None # never the case for our het networks

        fields = {
            GenerationMsgType.NEGOTIATE_ACK: ['min_time']
        }

        if msg_type in fields:
            for field in fields[msg_type]:
                setattr(self, field, kwargs.get(field))