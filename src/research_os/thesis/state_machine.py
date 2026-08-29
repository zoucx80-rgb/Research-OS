from .models import Thesis
class ThesisTransitionError(ValueError): pass
LEGAL={
 "new":{"active","expired"},"active":{"strengthening","weakening","falsified","expired"},
 "strengthening":{"active","weakening","falsified","expired"},"weakening":{"active","strengthening","falsified","expired"},
 "falsified":set(),"expired":set(),}
def transition_thesis(thesis:Thesis,new_status:str)->Thesis:
    if new_status not in LEGAL[thesis.status]: raise ThesisTransitionError(f"{thesis.status}->{new_status}")
    return thesis.model_copy(update={"status":new_status})
