
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.db import models

class Meta:
    verbose_name_plural = "Utenti"

class Stati_Ordini(models.Model):

    id = models.SmallAutoField(primary_key=True)
    stato = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.stato  # per Stati_Ordini

class Profili(models.Model):

    id = models.SmallAutoField(primary_key=True)
    ruolo = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.ruolo # per Stati_Ordini


def valida_multiplo_di_mille(value):
    if value % 1000 != 0:
        raise ValidationError(f"{value} non è un multiplo di 1000.")

class Utenti(AbstractUser):
    
    FL_OPE = [
        ('S', 'Si'),
        ('N', 'No'),
    ]

    RUOLI = [
        (1,'Amministratore'),
        (2,'Pianificazione'),
        (3,'Logistica'),
        (4,'Responsabile Produzione'),
        (5,'Commerciale'),
        (6,'Produzione'),
    ]

    id = models.AutoField(primary_key=id)
    nome = models.CharField(max_length=50,  null=True, blank=True)
    ruolo = models.ForeignKey(Profili,  on_delete=models.SET_NULL, null=True, blank=True)
    fl_ope = models.CharField(max_length=1, choices=FL_OPE, null=True, blank=True)

    def __str__(self):
        return f"{self.username} - {self.ruolo}"

class Avanzamento_Ordini(models.Model):
    
    FLAG = [
        ('S','Si'),
        ('N','No'),
    ]

    id = models.AutoField(primary_key=True)
    sede = models.CharField(max_length=50,  null=True, blank=True)
    ordine = models.CharField(max_length=50,null=True, blank=True)
    n_riga = models.IntegerField(validators=[valida_multiplo_di_mille])
    stato_ord = models.ForeignKey(Stati_Ordini, on_delete=models.SET_NULL, null=True, blank=True)
    operatore = models.ForeignKey(Utenti, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.CharField(max_length=100, null=True, blank=True)
    note_prod = models.CharField(max_length=100, null=True, blank=True)
    fl_note_prod = models.CharField(max_length=1, choices=FLAG, default='N')
    fl_note_ord = models.CharField(max_length=1, choices=FLAG, default='N')
    all_ord = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.sede} - {self.ordine} - {self.n_riga}"


class Profili_Stati(models.Model):
    
    USI = [
        ('V','Visione'),
        ('S', 'Scrittura'),
    ]

    RUOLI = [
        (1,'Amministratore'),
        (2,'Pianificazione'),
        (3,'Logistica'),
        (4,'Responsabile Produzione'),
        (5,'Commerciale'),
        (6,'Produzione'),
    ]

    id = models.AutoField(primary_key=True)
    ruolo = models.ForeignKey(Profili,  on_delete=models.SET_NULL, null=True, blank=True)
    tipo_uso = models.CharField(max_length=1, choices=USI, default='V')
    stato_ord = models.ForeignKey(Stati_Ordini, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.ruolo} - {self.tipo_uso} - {self.stato_ord}"    

    

class Note_Ordini(models.Model):

    id = models.AutoField(primary_key=True)
    sede = models.CharField(max_length=50,  null=True, blank=True)
    ordine = models.CharField(max_length=50)
    nota = models.CharField(max_length=100, null=True, blank=True)

class Note(models.Model):
    
    FLAG = [
        ('S','Si'),
        ('N','No'),
    ]
    id = models.AutoField(primary_key=True)
    sede = models.CharField(max_length=50,  null=True, blank=True)
    ordine = models.CharField(max_length=50, null=True, blank=True)
    testo = models.CharField(max_length=100,  null=True, blank=True)
    testo_prod = models.CharField(max_length=100,  null=True, blank=True)
    fl_upd = models.CharField(max_length=1, choices=FLAG, default='N')


"""class Log_Modifiche(models.Model):

    id = models.AutoField(primary_key=True)
    utente = models.BinaryField()
    data_mod = models.DateTimeField()
    sede = models.CharField(max_length=50,  null=True, blank=True)
    ordine = models.CharField(max_length=50)
    n_riga = models.IntegerField(validators=[valida_multiplo_di_mille])
    stato_ord = models.IntegerField(null=True, default=10)
    operatore = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)"""
    
