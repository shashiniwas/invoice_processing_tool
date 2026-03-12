import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(View):
    def post(self, request):
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        username = (payload.get('username') or '').strip()
        email = (payload.get('email') or '').strip()
        password = payload.get('password') or ''

        if not username or not password:
            return JsonResponse({'error': 'username and password are required'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'username already exists'}, status=409)

        user = User.objects.create_user(username=username, email=email, password=password)
        return JsonResponse({'id': user.id, 'username': user.username, 'email': user.email}, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(View):
    def post(self, request):
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        username = (payload.get('username') or '').strip()
        password = payload.get('password') or ''

        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)

        login(request, user)
        return JsonResponse({'message': 'Logged in successfully', 'username': user.username})


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Not authenticated'}, status=401)

        logout(request)
        return JsonResponse({'message': 'Logged out successfully'})


class ProfileView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Not authenticated'}, status=401)

        return JsonResponse({'id': request.user.id, 'username': request.user.username, 'email': request.user.email})
