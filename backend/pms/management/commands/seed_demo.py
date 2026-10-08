from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from pms.models import Hotel, Room, Unit, Reservation, CleaningTask, Maintenance
from pms.services import create_reservation, add_entry

class Command(BaseCommand):
    help = 'Carga datos ficticios en una base vacía. Nunca usar en un hotel en operación.'
    @transaction.atomic
    def handle(self,*args,**options):
        if Room.objects.exists() or Reservation.objects.exists():
            raise CommandError('La base ya tiene inventario o reservas. No se cargaron datos.')
        if not settings.DEBUG:
            raise CommandError('Los datos demo solo se cargan con DJANGO_DEBUG=1.')
        user,created=User.objects.get_or_create(username='recepcion',defaults={'is_staff':True,'is_superuser':True})
        if created:
            user.set_password('Nido-Prueba-2026!')
            user.save()
        Hotel.objects.get_or_create(pk=1)
        private=[]
        for name,rate in [('101 · Doble',62000),('102 · Doble',62000),('103 · Familiar',85000),('104 · Individual',45000)]:
            room=Room.objects.create(name=name,kind='PRIVATE',capacity=4 if 'Familiar' in name else 1 if 'Individual' in name else 2)
            private.append(Unit.objects.create(room=room,name='Habitación completa',rate=rate))
        beds=[]
        for name in ['201 · Dormitorio','202 · Dormitorio']:
            room=Room.objects.create(name=name,kind='SHARED',capacity=4)
            for i in range(1,5): beds.append(Unit.objects.create(room=room,name=f'Cama {i:02d}',rate=22000))
        today=timezone.localdate()
        records=[('Lucía Fernández',private[0],-2,2,2,'IN_HOUSE'),('Mateo Rivas',private[1],0,3,2,'CONFIRMED'),('Sofia y familia',private[2],2,5,4,'CONFIRMED'),('Emma Laurent',beds[0],-1,3,1,'IN_HOUSE'),('Tomás Silva',beds[1],0,2,1,'CONFIRMED'),('Noah Williams',beds[2],1,5,1,'CONFIRMED'),('Ana Torres',beds[4],-2,1,1,'IN_HOUSE'),('Liam Scott',beds[5],3,6,1,'CONFIRMED')]
        for guest,unit,offset,finish,guests,status in records:
            r=create_reservation({'guest':guest,'start':today+timedelta(days=offset),'end':today+timedelta(days=finish),'guests':guests,'unit_ids':[unit.pk],'contact':'','document':'','notes':''},user)
            if status=='IN_HOUSE':
                r.status=status
                r.checked_in_at=timezone.now()
                r.save()
                add_entry(r.pk,{'kind':'PAYMENT','description':'Anticipo','amount':Decimal('22000'),'method':'CASH'},user)
        Unit.objects.filter(pk=private[3].pk).update(cleaning='DIRTY')
        CleaningTask.objects.create(unit=private[3],note='Preparar para la próxima llegada')
        Maintenance.objects.create(room=beds[-1].room,unit=beds[-1],title='Revisar luz de lectura',notes='Lámpara de la cama superior',start=today,end=today+timedelta(days=2),blocking=True)
        self.stdout.write(self.style.SUCCESS('Datos ficticios creados. Cuenta de prueba documentada en README.md.'))
