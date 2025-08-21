# forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Usuario'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'})
    )



class CargarDocumentosForm(forms.Form):

    file_cuadroServicios = forms.FileField(
        label="Cuadro servicios Lunes - Viernes", required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'input-archivo', 'id':'archivoCuadroTurnos', 'required': False}))

    file_cuadroServiciosSabado = forms.FileField(
        label="Cuadro servicios Sabados", required= False,
        widget=forms.ClearableFileInput(attrs={'class': 'input-archivo', 'id':'archivoCuadroTurnosSabados'}))

    file_cuadroServiciosDomingo = forms.FileField(
        label="Cuadro servicios Domingos y Festivos", required= False,
        widget=forms.ClearableFileInput(attrs={'class': 'input-archivo', 'id':'archivoCuadroTurnosDomingo', 'required': False}))

    file_cuadroServiciosEspecial = forms.FileField(
        label="Cuadro servicios Especiales", required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'input-archivo', 'id':'archivoCuadroTurnosEspeciales', 'required': False}))
    
    file_sucesion = forms.FileField(
        label="Sucesión", required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'input-archivo', 'id':'archivoSucesion','required': False}))
    
class CargarSucesionOperadoresForm(forms.Form):
     file_sucesion = forms.FileField(
        label="Sucesión",
        widget=forms.ClearableFileInput(attrs={'class': 'input-archivo', 'id':'archivoSucesion'}))
    

    
class CargarDatosProno(forms.Form):
    file_cargarDatosProno = forms.FileField(
        label="Datos de revisión", required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'input-archivo', 'id':'archivoRevision', 'required': True}))


