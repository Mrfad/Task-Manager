from rest_framework.routers import DefaultRouter
from api.v1.views.tasks_views import TaskViewset

router = DefaultRouter()
router.register(r'tasks', TaskViewset, basename='tasks')

urlpatterns = router.urls