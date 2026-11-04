"""Integration adapter contracts."""
from abc import ABC,abstractmethod
class IntegrationAdapter(ABC):
    @abstractmethod
    def prepare(self,document_result:dict)->dict:
        """Map canonical extraction output into a downstream payload."""
        raise NotImplementedError
