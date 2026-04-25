class WorkflowError(RuntimeError): pass
class ProviderMissingError(WorkflowError): pass
class HumanGateRequired(WorkflowError): pass
