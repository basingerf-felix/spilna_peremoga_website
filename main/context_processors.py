# main/context_processors.py

def language_flags(request):
    return {
        'languages': [
            {'code': 'uk', 'flag': 'uk.png'},
            {'code': 'en', 'flag': 'en.png'},
            {'code': 'it', 'flag': 'it.png'},
        ]
    }
