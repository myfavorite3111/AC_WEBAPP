from django.shortcuts import render


def solutions(request):
    return render(request, "public_solutions.html")


def home(request):
    return render(request, "public_support.html")
