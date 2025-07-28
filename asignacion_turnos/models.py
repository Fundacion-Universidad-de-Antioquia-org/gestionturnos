from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Sucesion(models.Model):
    pos = models.IntegerField()
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20) # Codigo del conductor
    fecha = models.DateField()
    cedula = models.CharField(max_length= 20, null=True, blank=True)
    codigo_horario = models.CharField(max_length=20)
    cargo = models.CharField(max_length=50,blank=True, null=True)
    estado_inicio = models.CharField(max_length=50, blank=True, null=True)
    estado_fin = models.CharField(max_length=50, blank=True, null=True)
    hora_inicio = models.TimeField(blank=True, null=True)
    hora_fin = models.TimeField(blank=True, null=True)
    usuario_carga = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    fecha_carga = models.DateField(auto_now_add=True)
    estado_sucesion = models.CharField(max_length=50, default="revision")
    # Claves foraneas
    horario = models.ForeignKey('Horario',on_delete=models.SET_NULL, null=True,blank=True)
    empleado = models.ForeignKey('Empleado_Oddo',on_delete=models.SET_NULL,null=True,blank=True)

    def __str__(self):
        return f"{self.nombre} - {self.fecha}"

User = get_user_model()

class Horario(models.Model):
    horario = models.CharField("Nombre del Horario", max_length=100)
    fechavigencia = models.DateField("Fecha de Vigencia")
    fechaimplementacion = models.DateField("Fecha de Implementación")
    version = models.CharField("Versión", max_length=50)
    turno = models.CharField("Nombre del Turno", max_length=20)
    inihora = models.TimeField("Hora de Inicio", null=True, blank=True)                                         # Hora inicial del servicio
    inilugar = models.CharField("Lugar Inicio", max_length=100, null=True, blank=True)                          # Estación inicial del servicio
    inicir = models.CharField("Circuito Inicio", max_length=100, null=True, blank=True)
    deshora = models.TimeField("Hora de Despliegue", null=True, blank=True)
    deslugar = models.CharField("Lugar Despliegue", max_length=100, null=True, blank=True)
    desrelevo = models.CharField("Relevo Despliegue", max_length=100, null=True, blank=True)
    descir = models.CharField("Circuito Despliegue", max_length=100, null=True, blank=True)
    seghora = models.TimeField("Hora Segmento", null=True, blank=True)
    seglugar = models.CharField("Lugar Segmento", max_length=100, null=True, blank=True)
    segcir = models.CharField("Circuito Segmento", max_length=100, null=True, blank=True)
    finalhora = models.TimeField("Hora Final", null=True, blank=True)                                               # Hora final del servicio
    finallugar = models.CharField("Lugar Final", max_length=100, null=True, blank=True)                             # Estación  final del servicio
    finalrelevo = models.CharField("Relevo Final", max_length=100, null=True, blank=True)
    finbalcir = models.CharField("Circuito Final", max_length=100, null=True, blank=True)
    duracion = models.CharField("Duración Turno", max_length=50, null=True, blank=True)
    observaciones = models.TextField("Observaciones", null=True, blank=True)

    usuario_carga = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    fecha_carga = models.DateField(default= timezone.now, editable=True)

    class Meta:
        verbose_name = "Horario de Turno"
        verbose_name_plural = "Horarios de Turno"

    def __str__(self):
        return f"{self.turno} - {self.fechavigencia}"
    

class Empleado_Oddo(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=50)
    codigo = models.CharField(max_length=10)
    estado = models.CharField(max_length=15, null= True)
    cargo = models.CharField(max_length=50)
    #zona = models.BooleanField(default=False)
    formacion =models.CharField(max_length= 100, null=True)

    

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
        
    
class Solicitud_cambios_de_turnos(models.Model):
    codigo_solicitante = models.CharField(max_length=10)
    nombre_solicitante = models.CharField(max_length=100)
    cargo_solicitante = models.CharField(max_length= 50, null=True)
    turno_solicitante_original = models.CharField(max_length=10,  null=True)
    turno_solicitante_nuevo = models.CharField(max_length=10, null=True)
    codigo_receptor = models.CharField(max_length=10)
    nombre_receptor = models.CharField(max_length=100)
    cargo_receptor= models.CharField(max_length= 50, null=True)
    turno_receptor_original = models.CharField(max_length=10, null=True)
    turno_receptor_nuevo = models.CharField(max_length=10, null=True)
    fecha_solicitud_cambio = models.DateField(default=timezone.localdate, editable=True)



class Cambios_de_turnos(models.Model):
    codigo_solicitante = models.CharField(max_length=10)
    nombre_solicitante = models.CharField(max_length=100)
    cargo_solicitante = models.CharField(max_length= 50, null=True)
    formacion_solicitante = models.CharField(max_length=50, null=True)
    turno_solicitante_original = models.CharField(max_length=10,  null=True)
    turno_solicitante_nuevo = models.CharField(max_length=10, null=True)
    codigo_receptor = models.CharField(max_length=10)
    nombre_receptor = models.CharField(max_length=100)
    cargo_receptor= models.CharField(max_length= 50, null=True)
    formacion_receptor = models.CharField(max_length=50, null=True)
    turno_receptor_original = models.CharField(max_length=10, null=True)
    turno_receptor_nuevo = models.CharField(max_length=10, null=True)
    estado_cambio_emp = models.CharField(max_length=30, default='disponible', editable=True)
    estado_cambio_admin = models.CharField(max_length=30, default='pendiente')
    fecha_solicitud_cambio = models.DateField(default=timezone.localdate, editable=True)
    
    

    def __str__(self):
        return f"{self.fecha} - {self.codigo_solicitante} - {self.codigo_receptor}"
    
class Parametros(models.Model):
    hora_inicio_permitida_cambios = models.TimeField(max_length=10)
    hora_final_permitida_cambios = models.TimeField(max_length=10)
    dia_inicio_permitida_cambios = models.CharField(max_length=20)
    dia_final_permitida_cambios = models.CharField(max_length=20)

class Estados_servicios(models.Model):
    estado = models.CharField(max_length=20)
    fecha_carga = models.DateField(max_length=20,default=timezone.localdate)








