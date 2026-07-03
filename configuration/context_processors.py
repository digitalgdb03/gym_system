from .models import GymConfig


def gym_config(request):
    return {"gym": GymConfig.load()}
