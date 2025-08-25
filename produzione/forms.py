from django import forms
from django.contrib.auth import password_validation

class CambiaPasswordForm(forms.Form):
    vecchia_password = forms.CharField(
        label="Vecchia password",
        widget=forms.PasswordInput
    )
    nuova_password = forms.CharField(
        label="Nuova password",
        widget=forms.PasswordInput
    )
    conferma_nuova_password = forms.CharField(
        label="Conferma nuova password",
        widget=forms.PasswordInput
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned_data = super().clean()

        vecchia1 = cleaned_data.get('vecchia_password')
        nuova1 = cleaned_data.get('nuova_password')
        nuova2 = cleaned_data.get('conferma_nuova_password')

        if not self.user.check_password(vecchia1):
            raise forms.ValidationError("La vecchia password non è corretta.")

        if nuova1 != nuova2:
            raise forms.ValidationError("Le nuove password non coincidono.")

        # Validazione standard Django (contiene controllo di sicurezza)
        password_validation.validate_password(nuova1, self.user)

        return cleaned_data
