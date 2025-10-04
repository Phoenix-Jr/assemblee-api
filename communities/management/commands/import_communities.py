# management/commands/import_communities.py
"""
Commande Django pour importer toutes les données des communautés
Usage: python manage.py import_communities
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import datetime, date
from decimal import Decimal
from communities.models import (
    Country, City, Community, Pastor, Service, Ministry, MinistryActivity,
    Event, BibleStudy, ReadingProgram, Meditation, Leader, LeaderSpecialty,
    Baptism, BaptismRequirement, BaptismStatistics, Testimony, Gallery
)


class Command(BaseCommand):
    help = 'Importe les données complètes des communautés évangéliques'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Supprime toutes les données existantes avant l\'import',
        )
    
    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Début de l\'importation des données...'))
        
        # Optionnel : nettoyer les données existantes
        if options.get('clear'):
            self.stdout.write('Suppression des données existantes...')
            Community.objects.all().delete()
            Country.objects.all().delete()
        
        # Créer le pays et les villes
        congo, created = Country.objects.get_or_create(
            name='République du Congo',
            code='CG'
        )
        if created:
            self.stdout.write(f'✓ Pays créé: {congo.name}')
        
        pointe_noire, created = City.objects.get_or_create(
            name='Pointe-Noire',
            country=congo
        )
        if created:
            self.stdout.write(f'✓ Ville créée: {pointe_noire.name}')
        
        # Données complètes à importer
        communities_data = self.get_communities_data()
        
        # Importer chaque communauté
        success_count = 0
        for comm_key, comm_data in communities_data.items():
            try:
                self.import_community(comm_data, pointe_noire)
                success_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ {comm_data["fullName"]} importée avec succès'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Erreur pour {comm_key}: {str(e)}'))
        
        # Résumé
        self.stdout.write(self.style.SUCCESS(
            f'\n====================================\n'
            f'Importation terminée avec succès!\n'
            f'{success_count}/{len(communities_data)} communautés importées\n'
            f'===================================='
        ))
    
    def import_community(self, data, city):
        """Importe une communauté complète avec toutes ses données"""
        
        # Créer ou mettre à jour la communauté
        community, created = Community.objects.update_or_create(
            slug=data['id'],
            defaults={
                'name': data['name'],
                'full_name': data['fullName'],
                'founded_year': data['foundedYear'],
                'slogan': data['slogan'],
                'description': data['description'],
                'vision': data['vision'],
                'address': data['location']['address'],
                'city': city,
                'latitude': Decimal(str(data['location']['coordinates']['lat'])),
                'longitude': Decimal(str(data['location']['coordinates']['lng'])),
                'phone': data['contact']['phone'],
                'email': data['contact']['email'],
                'website': data['contact'].get('website', ''),
                'members_count': data['stats']['members'],
                'leaders_count': data['stats']['leaders'],
                'weekly_services_count': data['stats']['weeklyServices'],
                'baptisms_current_year': data['stats']['baptisms2024'],
            }
        )
        
        # Importer le pasteur principal
        pastor_data = data['pastor']
        pastor, _ = Pastor.objects.update_or_create(
            community=community,
            is_principal=True,
            defaults={
                'first_name': self.extract_first_name(pastor_data['name']),
                'last_name': self.extract_last_name(pastor_data['name']),
                'title': pastor_data['title'],
                'experience_years': int(pastor_data['experience'].split()[0]),
                'phone': pastor_data.get('phone', ''),
                'email': pastor_data.get('email', ''),
                'bio': pastor_data['bio'],
                'image_url': pastor_data.get('image', ''),
            }
        )
        
        # Importer les services
        Service.objects.filter(community=community).delete()  # Nettoyer les anciens
        for service_data in data['services']:
            day_map = {
                'Lundi': 1, 'Mardi': 2, 'Mercredi': 3, 'Jeudi': 4,
                'Vendredi': 5, 'Samedi': 6, 'Dimanche': 7
            }
            
            Service.objects.create(
                community=community,
                day=day_map[service_data['day']],
                time=self.parse_time(service_data['time']),
                type=service_data['type'],
                description=service_data['description'],
            )
        
        # Importer les ministères et leurs activités
        Ministry.objects.filter(community=community).delete()  # Nettoyer les anciens
        for ministry_data in data['ministries']:
            # Créer le leader
            leader, _ = Leader.objects.update_or_create(
                community=community,
                first_name=self.extract_first_name(ministry_data['leader']),
                last_name=self.extract_last_name(ministry_data['leader']),
                defaults={
                    'position': f"Responsable {ministry_data['name']}",
                    'experience_years': 5,
                }
            )
            
            # Créer le ministère
            ministry = Ministry.objects.create(
                community=community,
                name=ministry_data['name'],
                description=ministry_data['description'],
                leader=leader,
                participants_count=ministry_data['participants'],
                meeting_time=ministry_data['meetingTime'],
            )
            
            # Ajouter les activités
            for idx, activity in enumerate(ministry_data['activities']):
                MinistryActivity.objects.create(
                    ministry=ministry,
                    name=activity,
                    order=idx
                )
        
        # Importer les leaders spéciaux
        for leader_data in data.get('leadership', []):
            leader, _ = Leader.objects.update_or_create(
                community=community,
                first_name=self.extract_first_name(leader_data['name']),
                last_name=self.extract_last_name(leader_data['name']),
                defaults={
                    'position': leader_data['position'],
                    'experience_years': int(leader_data['experience'].split()[0]) if 'ans' in leader_data['experience'] else 5,
                }
            )
            
            # Ajouter les spécialités
            LeaderSpecialty.objects.filter(leader=leader).delete()
            for specialty in leader_data.get('specialties', []):
                LeaderSpecialty.objects.create(
                    leader=leader,
                    name=specialty
                )
        
        # Importer les événements
        Event.objects.filter(community=community).delete()
        for event_data in data.get('upcomingEvents', []):
            Event.objects.create(
                community=community,
                title=event_data['title'],
                date=datetime.strptime(event_data['date'], '%Y-%m-%d').date(),
                start_time=self.parse_time_range(event_data['time'])[0],
                end_time=self.parse_time_range(event_data['time'])[1] if '-' in event_data['time'] else None,
                type=self.map_event_type(event_data['type']),
                description=event_data['description'],
                location=event_data['location'],
                organizer=event_data['organizer'],
            )
        
        # Importer l'étude biblique
        if 'bibleStudy' in data:
            bs_data = data['bibleStudy']
            teacher = Leader.objects.filter(
                community=community,
                first_name__icontains=self.extract_first_name(bs_data['teacher'])
            ).first() or Leader.objects.filter(community=community).first()
            
            BibleStudy.objects.update_or_create(
                community=community,
                title=bs_data['currentSeries'],
                defaults={
                    'teacher': teacher,
                    'schedule': bs_data['schedule'],
                    'duration_weeks': int(bs_data['duration'].split()[0]),
                    'participants_count': bs_data['participants'],
                    'description': bs_data['description'],
                    'start_date': date.today(),
                    'is_active': True,
                }
            )
        
        # Importer le programme de lecture
        if 'readingProgram' in data:
            rp_data = data['readingProgram']
            coordinator_name = rp_data.get('coordinator', '')
            coordinator = None
            
            if coordinator_name:
                coordinator = Leader.objects.filter(
                    community=community,
                    first_name__icontains=self.extract_first_name(coordinator_name)
                ).first() or Leader.objects.filter(community=community).first()
            
            ReadingProgram.objects.update_or_create(
                community=community,
                title=rp_data['current'],
                defaults={
                    'participants_count': rp_data['participants'],
                    'progress_percentage': rp_data['progress'],
                    'current_book': rp_data.get('currentBook', rp_data.get('currentTheme', '')),
                    'weekly_reading': rp_data['weeklyReading'],
                    'coordinator': coordinator,
                    'next_milestone': rp_data.get('nextMilestone', ''),
                    'is_active': True,
                }
            )
        
        # Importer les méditations
        Meditation.objects.filter(community=community).delete()
        for meditation_data in data.get('meditations', []):
            author = Leader.objects.filter(
                community=community,
                first_name__icontains=self.extract_first_name(meditation_data['author'])
            ).first()
            
            Meditation.objects.create(
                community=community,
                title=meditation_data['title'],
                author=author,
                bible_verse=meditation_data['verse'],
                type=self.map_meditation_type(meditation_data['type']),
                category=self.map_meditation_category(meditation_data['category']),
                content=meditation_data['content'],
                duration_minutes=int(meditation_data['duration'].split()[0]),
                published_date=datetime.strptime(meditation_data['date'], '%Y-%m-%d').date(),
                is_published=True,
            )
        
        # Importer les baptêmes
        if 'baptisms' in data:
            if 'next' in data['baptisms']:
                baptism_data = data['baptisms']['next']
                coordinator_name = baptism_data.get('coordinator', '')
                coordinator = None
                
                if coordinator_name:
                    coordinator = Leader.objects.filter(
                        community=community,
                        first_name__icontains=self.extract_first_name(coordinator_name)
                    ).first() or Leader.objects.filter(community=community).first()
                
                Baptism.objects.update_or_create(
                    community=community,
                    date=datetime.strptime(baptism_data['date'], '%Y-%m-%d').date(),
                    defaults={
                        'time': self.parse_time(baptism_data['time']),
                        'location': baptism_data['location'],
                        'candidates_count': baptism_data['candidates'],
                        'preparation_sessions': baptism_data['preparationSessions'],
                        'coordinator': coordinator,
                        'is_completed': False,
                    }
                )
            
            # Ajouter les exigences de baptême
            if 'requirements' in data['baptisms']:
                BaptismRequirement.objects.filter(community=community).delete()
                for idx, req in enumerate(data['baptisms']['requirements']):
                    BaptismRequirement.objects.create(
                        community=community,
                        requirement=req,
                        order=idx
                    )
            
            # Ajouter les statistiques de baptême
            if 'statistics' in data['baptisms']:
                stats = data['baptisms']['statistics']
                BaptismStatistics.objects.update_or_create(
                    community=community,
                    year=2024,
                    defaults={'count': stats['thisYear']}
                )
                BaptismStatistics.objects.update_or_create(
                    community=community,
                    year=2023,
                    defaults={'count': stats['lastYear']}
                )
        
        # Importer les témoignages
        for testimony_data in data.get('testimonies', []):
            Testimony.objects.update_or_create(
                community=community,
                title=testimony_data['title'],
                author_name=testimony_data['author'],
                defaults={
                    'category': self.map_testimony_category(testimony_data['category']),
                    'excerpt': testimony_data['excerpt'],
                    'full_content': testimony_data['excerpt'] + '... (suite du témoignage)',
                    'date': datetime.strptime(testimony_data['date'], '%Y-%m-%d').date(),
                    'is_published': True,
                    'is_verified': True,
                }
            )
        
        # Importer les galeries
        for gallery_data in data.get('galleries', []):
            Gallery.objects.update_or_create(
                community=community,
                title=gallery_data['title'],
                defaults={
                    'images_count': gallery_data['images'],
                    'cover_image_url': gallery_data['cover'],
                    'is_public': True,
                }
            )
    
    def extract_first_name(self, full_name):
        """Extrait le prénom d'un nom complet"""
        name = full_name.replace('Pasteur ', '').replace('Sœur ', '').replace('Frère ', '')
        parts = name.split()
        return parts[0] if parts else ''
    
    def extract_last_name(self, full_name):
        """Extrait le nom de famille d'un nom complet"""
        name = full_name.replace('Pasteur ', '').replace('Sœur ', '').replace('Frère ', '')
        parts = name.split()
        return ' '.join(parts[1:]) if len(parts) > 1 else parts[0] if parts else ''
    
    def parse_time(self, time_str):
        """Parse une chaîne de temps au format HH:MM"""
        if not time_str:
            return datetime.strptime('00:00', '%H:%M').time()
        
        # Nettoyer et standardiser le format
        time_str = time_str.strip()
        time_str = time_str.replace('h', ':').replace('H', ':')
        
        # Gérer différents formats
        if ':' not in time_str:
            # Format comme "10h00" devient "10:00"
            if len(time_str) == 2:
                time_str = time_str + ':00'
            elif len(time_str) == 4:
                time_str = time_str[:2] + ':' + time_str[2:]
        
        # S'assurer qu'on a bien HH:MM
        parts = time_str.split(':')
        if len(parts) == 2:
            hour = parts[0].zfill(2)
            minute = parts[1][:2].zfill(2) if parts[1] else '00'
            time_str = f'{hour}:{minute}'
        
        try:
            return datetime.strptime(time_str, '%H:%M').time()
        except:
            return datetime.strptime('00:00', '%H:%M').time()
    
    def parse_time_range(self, time_str):
        """Parse une plage horaire comme '14h00 - 18h00'"""
        if '-' in time_str:
            parts = time_str.split('-')
            start = self.parse_time(parts[0].strip())
            end = self.parse_time(parts[1].strip()) if len(parts) > 1 else None
            return start, end
        else:
            return self.parse_time(time_str), None
    
    def map_event_type(self, type_str):
        """Mappe le type d'événement"""
        type_map = {
            'Spirituel': 'spiritual',
            'Sacrement': 'sacrament',
            'Formation': 'formation',
            'Culturel': 'cultural',
            'Social': 'social',
            'Évangélisation': 'evangelization',
        }
        return type_map.get(type_str, 'other')
    
    def map_meditation_type(self, type_str):
        """Mappe le type de méditation"""
        type_map = {
            'Méditation quotidienne': 'daily',
            'Réflexion hebdomadaire': 'weekly',
            'Méditation jeunesse': 'youth',
            'Méditation communautaire': 'community',
            'Méditation professionnelle': 'professional',
            'Méditation artistique': 'artistic',
            'Méditation étudiante': 'student',
        }
        return type_map.get(type_str, 'daily')
    
    def map_meditation_category(self, category_str):
        """Mappe la catégorie de méditation"""
        category_map = {
            'Encouragement': 'encouragement',
            'Vie chrétienne': 'christian_life',
            'Relations': 'relationships',
            'Communauté': 'community',
            'Créativité': 'creativity',
            'Travail': 'work',
            'Sagesse': 'wisdom',
            'Foi': 'faith',
        }
        return category_map.get(category_str, 'faith')
    
    def map_testimony_category(self, category_str):
        """Mappe la catégorie de témoignage"""
        category_map = {
            'Guérison': 'healing',
            'Provision': 'provision',
            'Salut': 'salvation',
            'Délivrance': 'deliverance',
            'Relations': 'relationship',
            'Professionnel': 'professional',
        }
        return category_map.get(category_str, 'other')
    
    def get_communities_data(self):
        """Retourne toutes les données des communautés"""
        return {
            'mpita': {
                'id': 'mpita',
                'name': 'Mpita',
                'fullName': 'Assemblée Évangélique Mpita',
                'foundedYear': 1998,
                'slogan': "Fondement de la foi, pilier de l'espérance",
                'pastor': {
                    'name': 'Pasteur Jean-Claude Mbeki',
                    'title': 'Pasteur Principal',
                    'experience': '15 ans de ministère',
                    'phone': '+242 05 123 4567',
                    'email': 'jc.mbeki@assemblee-evangelique.cg',
                    'bio': "Pasteur Jean-Claude Mbeki dirige la communauté Mpita depuis sa fondation en 1998. Diplômé en théologie de l'Institut Biblique de Brazzaville, il a à cœur l'évangélisation et la formation des leaders.",
                    'image': 'https://images.unsplash.com/photo-1717201611909-0f75ee9b0b1e'
                },
                'location': {
                    'address': "Avenue de l'Indépendance, Quartier Mpita",
                    'city': 'Pointe-Noire',
                    'country': 'République du Congo',
                    'coordinates': {'lat': -4.7692, 'lng': 11.8639}
                },
                'contact': {
                    'phone': '+242 05 123 4567',
                    'email': 'mpita@assemblee-evangelique.cg',
                    'website': 'mpita.assemblee-evangelique.cg'
                },
                'stats': {
                    'members': 450,
                    'leaders': 25,
                    'ministries': 8,
                    'weeklyServices': 6,
                    'baptisms2024': 45
                },
                'description': "Notre première communauté, fondée en 1998, est le berceau de l'Assemblée Évangélique. Située au cœur du quartier Mpita, elle accueille une famille diverse et dynamique, unie par la foi et l'amour du Christ.",
                'vision': "Être une communauté rayonnante qui forme des disciples passionnés de Jésus-Christ, engagés dans la transformation de leur quartier et de leur nation.",
                'services': [
                    {'day': 'Dimanche', 'time': '10h00', 'type': 'Culte Principal', 'description': 'Service dominical avec louange, prédication et communion'},
                    {'day': 'Mercredi', 'time': '18h00', 'type': 'Culte de Milieu de Semaine', 'description': "Temps de prière et d'enseignement"},
                    {'day': 'Vendredi', 'time': '19h00', 'type': 'Groupe de Jeunes', 'description': 'Activités et formation pour les 15-30 ans'},
                    {'day': 'Lundi', 'time': '18h30', 'type': 'Cellules de Prière', 'description': 'Groupes de prière dans les maisons'},
                    {'day': 'Mardi', 'time': '18h00', 'type': 'Chorale', 'description': 'Répétition et formation musicale'},
                    {'day': 'Jeudi', 'time': '19h00', 'type': 'Formation Leadership', 'description': 'École de formation des leaders'}
                ],
                'ministries': [
                    {
                        'name': 'Ministère Enfance',
                        'leader': 'Sœur Marie Nkounkou',
                        'participants': 85,
                        'description': 'École du dimanche, camps de vacances et activités créatives',
                        'activities': ['École du dimanche', 'Camps de vacances', 'Spectacle de Noël', 'Club de lecture biblique'],
                        'meetingTime': 'Dimanche 9h00'
                    },
                    {
                        'name': 'Ministère Jeunesse',
                        'leader': 'Frère Samuel Ngoyi',
                        'participants': 120,
                        'description': 'Formation, sorties et évangélisation pour les 15-30 ans',
                        'activities': ['Groupe de jeunes', 'Camps spirituels', 'Évangélisation de rue', 'Formations professionnelles'],
                        'meetingTime': 'Vendredi 19h00'
                    },
                    {
                        'name': 'Ministère Femmes',
                        'leader': 'Sœur Grace Makaya',
                        'participants': 95,
                        'description': 'Soutien, formation et entraide entre les femmes',
                        'activities': ['Réunions mensuelles', 'Couture et artisanat', 'Visites aux malades', 'Conseil matrimonial'],
                        'meetingTime': 'Premier samedi du mois 15h00'
                    },
                    {
                        'name': 'Ministère Hommes',
                        'leader': 'Frère Paul Loubaki',
                        'participants': 65,
                        'description': 'Formation masculine et responsabilité familiale',
                        'activities': ['Petit-déjeuner mensuel', 'Projets communautaires', 'Mentorat', 'Évangélisation'],
                        'meetingTime': 'Deuxième samedi du mois 8h00'
                    },
                    {
                        'name': 'Ministère Musical',
                        'leader': 'Sœur Marie Kouka',
                        'participants': 40,
                        'description': 'Louange et formation musicale',
                        'activities': ['Chorale principale', 'Groupe de jeunes', 'Formation musicale', 'Enregistrements'],
                        'meetingTime': 'Mardi 18h00, Samedi 15h00'
                    },
                    {
                        'name': 'Ministère Compassion',
                        'leader': 'Frère Emmanuel Mboko',
                        'participants': 30,
                        'description': 'Action sociale et aide aux démunis',
                        'activities': ['Distribution alimentaire', 'Visites aux malades', 'Aide scolaire', "Projets d'eau"],
                        'meetingTime': 'Samedi 17h00'
                    }
                ],
                'upcomingEvents': [
                    {
                        'title': 'Nuit de Prière et de Jeûne',
                        'date': '2024-09-20',
                        'time': '18h00 - 06h00',
                        'type': 'Spirituel',
                        'description': 'Nuit dédiée à la prière pour notre ville et notre nation',
                        'organizer': 'Ministère de Prière',
                        'location': 'Sanctuaire principal'
                    },
                    {
                        'title': 'Baptême Collectif',
                        'date': '2024-09-29',
                        'time': '10h00 - 12h00',
                        'type': 'Sacrement',
                        'description': 'Cérémonie de baptême pour 12 nouveaux membres',
                        'organizer': 'Équipe Pastorale',
                        'location': 'Plage de Côte Sauvage'
                    },
                    {
                        'title': 'Camp de Jeunes',
                        'date': '2024-10-05',
                        'time': '3 jours',
                        'type': 'Formation',
                        'description': 'Retraite spirituelle pour les 15-30 ans',
                        'organizer': 'Ministère Jeunesse',
                        'location': 'Centre de retraite Mayumba'
                    }
                ],
                'bibleStudy': {
                    'currentSeries': 'Les Paraboles de Jésus',
                    'teacher': 'Pasteur Jean-Claude Mbeki',
                    'schedule': 'Mercredi 19h30',
                    'duration': '8 semaines',
                    'participants': 75,
                    'description': 'Étude approfondie des paraboles et leur application dans notre vie quotidienne',
                    'materials': ["Cahier d'étude", "Bible d'étude", 'Supports audio'],
                    'nextStudy': {
                        'title': 'Les Épîtres de Paul',
                        'startDate': '2024-11-06',
                        'teacher': 'Pasteur adjoint Pierre Malonga'
                    }
                },
                'readingProgram': {
                    'current': 'Lecture Biblique Annuelle',
                    'participants': 180,
                    'progress': 68,
                    'currentBook': 'Livre des Psaumes',
                    'weeklyReading': 'Psaumes 90-96',
                    'coordinator': 'Sœur Béatrice Nzamba',
                    'resources': ['Plan de lecture', 'Application mobile', 'Groupe WhatsApp', 'Réunions hebdomadaires'],
                    'nextMilestone': 'Achèvement des Psaumes - 30 septembre'
                },
                'meditations': [
                    {
                        'title': 'La Paix dans la Tempête',
                        'author': 'Pasteur Jean-Claude Mbeki',
                        'date': '2024-09-14',
                        'verse': 'Marc 4:39',
                        'type': 'Méditation quotidienne',
                        'content': 'Dans les moments difficiles de notre vie, souvenons-nous que Jésus a le pouvoir de calmer toutes les tempêtes...',
                        'duration': '5 min',
                        'category': 'Encouragement'
                    },
                    {
                        'title': 'Marcher dans la Lumière',
                        'author': 'Sœur Grace Makaya',
                        'date': '2024-09-13',
                        'verse': '1 Jean 1:7',
                        'type': 'Réflexion hebdomadaire',
                        'content': 'La lumière de Christ nous guide chaque jour. Comment pouvons-nous refléter cette lumière dans notre quotidien ?',
                        'duration': '8 min',
                        'category': 'Vie chrétienne'
                    },
                    {
                        'title': "L'Amour qui Transforme",
                        'author': 'Frère Samuel Ngoyi',
                        'date': '2024-09-12',
                        'verse': '1 Corinthiens 13:4',
                        'type': 'Méditation jeunesse',
                        'content': "L'amour de Dieu a le pouvoir de transformer nos relations et notre communauté...",
                        'duration': '6 min',
                        'category': 'Relations'
                    }
                ],
                'leadership': [
                    {
                        'name': 'Pasteur Jean-Claude Mbeki',
                        'position': 'Pasteur Principal',
                        'ministry': 'Direction générale',
                        'experience': '15 ans',
                        'specialties': ['Prédication', 'Formation de leaders', 'Évangélisation']
                    },
                    {
                        'name': 'Sœur Marie Nkounkou',
                        'position': 'Responsable Enfance',
                        'ministry': 'Ministère Enfance',
                        'experience': '8 ans',
                        'specialties': ['Pédagogie chrétienne', 'Animation', 'Formation des moniteurs']
                    },
                    {
                        'name': 'Frère Samuel Ngoyi',
                        'position': 'Responsable Jeunesse',
                        'ministry': 'Ministère Jeunesse',
                        'experience': '5 ans',
                        'specialties': ['Accompagnement jeunes', 'Évangélisation', 'Musique']
                    },
                    {
                        'name': 'Sœur Grace Makaya',
                        'position': 'Responsable Femmes',
                        'ministry': 'Ministère Femmes',
                        'experience': '10 ans',
                        'specialties': ['Conseil féminin', 'Action sociale', 'Formation']
                    }
                ],
                'baptisms': {
                    'next': {
                        'date': '2024-09-29',
                        'time': '10h00',
                        'location': 'Plage de Côte Sauvage',
                        'candidates': 12,
                        'preparationSessions': 4,
                        'coordinator': 'Pasteur Jean-Claude Mbeki'
                    },
                    'requirements': [
                        'Avoir accepté Jésus-Christ comme Sauveur personnel',
                        'Suivre les 4 sessions de préparation',
                        'Témoignage public de sa foi',
                        'Engagement à vivre selon les principes bibliques'
                    ],
                    'statistics': {
                        'thisYear': 45,
                        'lastYear': 38,
                        'total': 520
                    }
                },
                'testimonies': [
                    {
                        'author': 'Sœur Antoinette Malonga',
                        'title': 'Guérison Divine',
                        'date': '2024-08-20',
                        'category': 'Guérison',
                        'excerpt': "Après des années de maladie, Dieu m'a complètement guérie lors d'une nuit de prière..."
                    },
                    {
                        'author': 'Frère David Kimbembe',
                        'title': 'Provision Divine',
                        'date': '2024-08-15',
                        'category': 'Provision',
                        'excerpt': "Sans emploi depuis 6 mois, j'ai vu la main de Dieu pourvoir miraculeusement..."
                    }
                ],
                'galleries': [
                    {
                        'title': 'Baptême Collectif - Août 2024',
                        'images': 12,
                        'cover': 'https://images.unsplash.com/photo-1741485745396-47004ac8c248'
                    },
                    {
                        'title': 'Camp de Jeunes 2024',
                        'images': 25,
                        'cover': 'https://images.unsplash.com/photo-1672867138294-8aa5591041de'
                    }
                ]
            },
            
            'plateaux': {
                'id': 'plateaux',
                'name': 'Plateaux',
                'fullName': 'Assemblée Évangélique Plateaux',
                'foundedYear': 2005,
                'slogan': 'Élevés pour élever',
                'pastor': {
                    'name': 'Pasteur Marie-Rose Nkounkou',
                    'title': 'Pasteur Principal',
                    'experience': '12 ans de ministère',
                    'phone': '+242 05 234 5678',
                    'email': 'mr.nkounkou@assemblee-evangelique.cg',
                    'bio': "Pasteur Marie-Rose Nkounkou a fondé la communauté Plateaux en 2005. Spécialisée dans le ministère familial et l'accompagnement des femmes, elle apporte une vision moderne et inclusive.",
                    'image': 'https://images.unsplash.com/photo-1717201611909-0f75ee9b0b1e'
                },
                'location': {
                    'address': 'Rue des Palmiers, Quartier Plateaux',
                    'city': 'Pointe-Noire',
                    'country': 'République du Congo',
                    'coordinates': {'lat': -4.7502, 'lng': 11.8853}
                },
                'contact': {
                    'phone': '+242 05 234 5678',
                    'email': 'plateaux@assemblee-evangelique.cg',
                    'website': 'plateaux.assemblee-evangelique.cg'
                },
                'stats': {
                    'members': 320,
                    'leaders': 18,
                    'ministries': 7,
                    'weeklyServices': 5,
                    'baptisms2024': 32
                },
                'description': "Implantée en 2005, notre communauté des Plateaux rayonne par son engagement social et son ministère jeunesse particulièrement actif. Nous sommes reconnus pour notre approche innovante et notre ouverture à la modernité.",
                'vision': 'Construire une communauté moderne et dynamique qui forme des familles solides et des leaders influents dans la société.',
                'services': [
                    {'day': 'Dimanche', 'time': '9h00', 'type': 'École du Dimanche', 'description': 'Formation biblique pour tous les âges'},
                    {'day': 'Dimanche', 'time': '10h30', 'type': 'Culte Principal', 'description': 'Service dominical contemporain'},
                    {'day': 'Jeudi', 'time': '18h30', 'type': 'Service de Prière', 'description': 'Intercession pour les familles'},
                    {'day': 'Samedi', 'time': '16h00', 'type': 'Activités Familiales', 'description': 'Temps de communion familiale'},
                    {'day': 'Mercredi', 'time': '19h30', 'type': 'Cellule Professionnels', 'description': 'Groupe pour jeunes actifs'}
                ],
                'ministries': [
                    {
                        'name': 'Ministère Familial',
                        'leader': 'Pasteur Marie-Rose Nkounkou',
                        'participants': 75,
                        'description': 'Accompagnement des couples et des familles',
                        'activities': ['Conseil matrimonial', 'Préparation au mariage', 'Séminaires familiaux', 'Médiation'],
                        'meetingTime': 'Samedi 16h00'
                    },
                    {
                        'name': 'Ministère Jeunes Professionnels',
                        'leader': 'Frère Daniel Moussa',
                        'participants': 45,
                        'description': 'Réseau et formation pour jeunes actifs',
                        'activities': ['Networking chrétien', 'Formation leadership', 'Mentorat professionnel', "Projets d'entreprise"],
                        'meetingTime': 'Mercredi 19h30'
                    },
                    {
                        'name': 'Ministère Créatif',
                        'leader': 'Sœur Esther Milandou',
                        'participants': 35,
                        'description': 'Arts, créativité et expression artistique',
                        'activities': ['Théâtre chrétien', 'Arts visuels', 'Poésie', "Décoration d'église"],
                        'meetingTime': 'Vendredi 18h00'
                    },
                    {
                        'name': 'Ministère Social',
                        'leader': 'Frère Joseph Ngoma',
                        'participants': 50,
                        'description': 'Action sociale et communautaire',
                        'activities': ['Aide aux démunis', "Projets d'éducation", 'Santé communautaire', 'Micro-finance'],
                        'meetingTime': 'Samedi 14h00'
                    }
                ],
                'upcomingEvents': [
                    {
                        'title': 'Conférence Mariage et Famille',
                        'date': '2024-09-22',
                        'time': '14h00 - 18h00',
                        'type': 'Formation',
                        'description': 'Séminaire sur la construction de familles solides',
                        'organizer': 'Ministère Familial',
                        'location': 'Centre Communautaire'
                    },
                    {
                        'title': 'Soirée Créative',
                        'date': '2024-09-28',
                        'time': '19h00 - 22h00',
                        'type': 'Culturel',
                        'description': "Exposition d'arts et spectacle",
                        'organizer': 'Ministère Créatif',
                        'location': 'Salle polyvalente'
                    }
                ],
                'bibleStudy': {
                    'currentSeries': 'Les Béatitudes',
                    'teacher': 'Pasteur Marie-Rose Nkounkou',
                    'schedule': 'Jeudi 19h30',
                    'duration': '6 semaines',
                    'participants': 55,
                    'description': 'Exploration des Béatitudes et leur impact sur notre vie moderne',
                    'materials': ["Guide d'étude", 'Vidéos explicatives', 'Questions de réflexion'],
                    'nextStudy': {
                        'title': 'Les Femmes de la Bible',
                        'startDate': '2024-10-10',
                        'teacher': 'Sœur Esther Milandou'
                    }
                },
                'readingProgram': {
                    'current': 'Lecture Thématique',
                    'participants': 125,
                    'progress': 45,
                    'currentTheme': 'La Famille dans la Bible',
                    'weeklyReading': 'Éphésiens 5-6',
                    'coordinator': 'Frère Daniel Moussa',
                    'resources': ['Guide thématique', 'Discussions en groupe', 'Fiches de réflexion'],
                    'nextMilestone': 'Thème suivant: Leadership - 1er octobre'
                },
                'meditations': [
                    {
                        'title': "L'Unité dans la Diversité",
                        'author': 'Pasteur Marie-Rose Nkounkou',
                        'date': '2024-09-14',
                        'verse': '1 Corinthiens 12:12',
                        'type': 'Méditation communautaire',
                        'content': "Notre diversité est notre richesse quand elle est unie par l'amour du Christ...",
                        'duration': '7 min',
                        'category': 'Communauté'
                    },
                    {
                        'title': 'La Créativité, Don de Dieu',
                        'author': 'Sœur Esther Milandou',
                        'date': '2024-09-13',
                        'verse': 'Exode 35:31',
                        'type': 'Méditation artistique',
                        'content': 'Dieu nous a créés créatifs. Comment utilisons-nous nos talents pour Sa gloire ?',
                        'duration': '5 min',
                        'category': 'Créativité'
                    }
                ],
                'leadership': [
                    {
                        'name': 'Pasteur Marie-Rose Nkounkou',
                        'position': 'Pasteur Principal',
                        'ministry': 'Direction générale',
                        'experience': '12 ans',
                        'specialties': ['Ministère familial', 'Conseil', 'Formation des femmes']
                    },
                    {
                        'name': 'Frère Daniel Moussa',
                        'position': 'Responsable Jeunes Professionnels',
                        'ministry': 'Ministère Professionnel',
                        'experience': '6 ans',
                        'specialties': ['Leadership', 'Mentorat', 'Développement personnel']
                    }
                ],
                'baptisms': {
                    'next': {
                        'date': '2024-10-13',
                        'time': '15h00',
                        'location': "Baptistère de l'église",
                        'candidates': 8,
                        'preparationSessions': 6,
                        'coordinator': 'Pasteur Marie-Rose Nkounkou'
                    },
                    'requirements': [
                        'Acceptation personnelle de Jésus-Christ',
                        'Participation aux sessions de préparation',
                        "Témoignage devant l'assemblée",
                        "Engagement dans la vie de l'église"
                    ],
                    'statistics': {
                        'thisYear': 32,
                        'lastYear': 28,
                        'total': 285
                    }
                },
                'testimonies': [],
                'galleries': []
            },
            
            'centreville': {
                'id': 'centreville',
                'name': 'Centre-Ville',
                'fullName': 'Assemblée Évangélique Centre-Ville',
                'foundedYear': 2012,
                'slogan': 'Au cœur de la ville, au cœur de Dieu',
                'pastor': {
                    'name': 'Pasteur David Loubaki',
                    'title': 'Pasteur Principal',
                    'experience': '8 ans de ministère',
                    'phone': '+242 05 345 6789',
                    'email': 'd.loubaki@assemblee-evangelique.cg',
                    'bio': "Pasteur David Loubaki a lancé la communauté Centre-Ville en 2012 avec une vision d'atteindre les professionnels et les étudiants du centre urbain. Il est reconnu pour son approche contemporaine.",
                    'image': 'https://images.unsplash.com/photo-1706381077572-24b367980d20'
                },
                'location': {
                    'address': 'Boulevard Maréchal Lyautey, Centre-Ville',
                    'city': 'Pointe-Noire',
                    'country': 'République du Congo',
                    'coordinates': {'lat': -4.7938, 'lng': 11.8684}
                },
                'contact': {
                    'phone': '+242 05 345 6789',
                    'email': 'centreville@assemblee-evangelique.cg',
                    'website': 'centreville.assemblee-evangelique.cg'
                },
                'stats': {
                    'members': 280,
                    'leaders': 15,
                    'ministries': 6,
                    'weeklyServices': 4,
                    'baptisms2024': 28
                },
                'description': "Notre plus récente communauté, établie en 2012, se distingue par son approche moderne et son outreach vers les professionnels du centre-ville. Nous privilégions l'innovation dans l'évangélisation.",
                'vision': "Être un phare spirituel au cœur de la ville, touchant les professionnels, étudiants et familles urbaines avec l'amour transformateur du Christ.",
                'services': [
                    {'day': 'Dimanche', 'time': '10h30', 'type': 'Culte Principal', 'description': 'Service contemporain avec focus évangélisation'},
                    {'day': 'Mardi', 'time': '19h00', 'type': 'Étude Biblique', 'description': 'Étude approfondie interactive'},
                    {'day': 'Vendredi', 'time': '18h00', 'type': 'Culte de Fin de Semaine', 'description': 'Préparation spirituelle week-end'},
                    {'day': 'Samedi', 'time': '08h00', 'type': "Petit-déjeuner d'Hommes", 'description': 'Fellowship masculin mensuel'}
                ],
                'ministries': [
                    {
                        'name': 'Ministère Urbain',
                        'leader': 'Pasteur David Loubaki',
                        'participants': 60,
                        'description': 'Évangélisation et implantation urbaine',
                        'activities': ['Évangélisation de rue', 'Cafés spirituels', 'Conférences publiques', 'Réseaux sociaux'],
                        'meetingTime': 'Samedi 15h00'
                    },
                    {
                        'name': 'Ministère Étudiant',
                        'leader': 'Frère Arsène Mbouma',
                        'participants': 85,
                        'description': 'Accompagnement des étudiants',
                        'activities': ["Groupe d'étude", "Bourses d'aide", 'Mentorat académique', 'Orientation professionnelle'],
                        'meetingTime': 'Jeudi 19h00'
                    },
                    {
                        'name': 'Ministère Technologique',
                        'leader': 'Sœur Grace Tech',
                        'participants': 25,
                        'description': "Innovation et technologie au service de l'Évangile",
                        'activities': ['Streaming en direct', 'Applications mobiles', 'Réseaux sociaux', 'Formations numériques'],
                        'meetingTime': 'Mercredi 18h00'
                    }
                ],
                'upcomingEvents': [
                    {
                        'title': 'Petit-déjeuner Leadership',
                        'date': '2024-09-21',
                        'time': '08h00 - 10h00',
                        'type': 'Formation',
                        'description': 'Formation leadership pour professionnels',
                        'organizer': 'Ministère Urbain',
                        'location': 'Salle de conférence'
                    },
                    {
                        'title': 'Café Spirituel',
                        'date': '2024-09-25',
                        'time': '18h30 - 20h30',
                        'type': 'Évangélisation',
                        'description': 'Discussions ouvertes sur la foi',
                        'organizer': 'Ministère Urbain',
                        'location': 'Café partenaire centre-ville'
                    }
                ],
                'bibleStudy': {
                    'currentSeries': 'Daniel dans la Cour Royale',
                    'teacher': 'Pasteur David Loubaki',
                    'schedule': 'Mardi 19h00',
                    'duration': '10 semaines',
                    'participants': 65,
                    'description': 'Comment vivre sa foi dans un environnement professionnel séculier',
                    'materials': ["Livre d'étude", 'Application mobile', 'Podcasts complémentaires'],
                    'nextStudy': {
                        'title': 'Les Proverbes et la Sagesse',
                        'startDate': '2024-11-19',
                        'teacher': "Équipe d'enseignement"
                    }
                },
                'readingProgram': {
                    'current': 'Bible en Une Année',
                    'participants': 95,
                    'progress': 72,
                    'currentBook': 'Livre des Proverbes',
                    'weeklyReading': 'Proverbes 20-26',
                    'coordinator': 'Sœur Rachel Ngoma',
                    'resources': ['Application Bible', 'Rappels SMS', 'Groupe de discussion en ligne'],
                    'nextMilestone': 'Achèvement Ancien Testament - 15 octobre'
                },
                'meditations': [
                    {
                        'title': 'Excellence dans le Travail',
                        'author': 'Pasteur David Loubaki',
                        'date': '2024-09-14',
                        'verse': 'Colossiens 3:23',
                        'type': 'Méditation professionnelle',
                        'content': 'Comment honorer Dieu dans notre travail quotidien et être des témoins efficaces...',
                        'duration': '6 min',
                        'category': 'Travail'
                    },
                    {
                        'title': 'Sagesse pour les Décisions',
                        'author': 'Frère Arsène Mbouma',
                        'date': '2024-09-13',
                        'verse': 'Proverbes 3:5-6',
                        'type': 'Méditation étudiante',
                        'content': 'Prendre des décisions sages dans nos études et notre avenir professionnel...',
                        'duration': '4 min',
                        'category': 'Sagesse'
                    }
                ],
                'leadership': [
                    {
                        'name': 'Pasteur David Loubaki',
                        'position': 'Pasteur Principal',
                        'ministry': 'Direction générale',
                        'experience': '8 ans',
                        'specialties': ['Évangélisation urbaine', 'Leadership', 'Innovation']
                    },
                    {
                        'name': 'Frère Arsène Mbouma',
                        'position': 'Responsable Étudiants',
                        'ministry': 'Ministère Étudiant',
                        'experience': '4 ans',
                        'specialties': ['Accompagnement jeunes', 'Orientation', 'Formation']
                    }
                ],
                'baptisms': {
                    'next': {
                        'date': '2024-10-27',
                        'time': '11h00',
                        'location': "Baptistère moderne de l'église",
                        'candidates': 6,
                        'preparationSessions': 4,
                        'coordinator': 'Pasteur David Loubaki'
                    },
                    'requirements': [
                        'Décision personnelle pour Christ',
                        'Formation biblique de base',
                        'Témoignage public',
                        'Engagement dans un ministère'
                    ],
                    'statistics': {
                        'thisYear': 28,
                        'lastYear': 22,
                        'total': 156
                    }
                },
                'testimonies': [],
                'galleries': []
            }
        }