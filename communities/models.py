# models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# Modèles de base
class TimeStampedModel(models.Model):
    """Modèle abstrait pour ajouter les timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class Country(models.Model):
    """Modèle pour les pays"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=3, unique=True)
    
    class Meta:
        verbose_name = "Pays"
        verbose_name_plural = "Pays"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class City(models.Model):
    """Modèle pour les villes"""
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='cities')
    
    class Meta:
        verbose_name = "Ville"
        verbose_name_plural = "Villes"
        unique_together = ['name', 'country']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name}, {self.country.name}"


# Modèles principaux
class Community(TimeStampedModel):
    """Modèle principal pour une communauté"""
    # Identifiants et informations de base
    slug = models.SlugField(max_length=50, unique=True, help_text="Identifiant unique pour URLs")
    name = models.CharField(max_length=100, verbose_name="Nom court")
    full_name = models.CharField(max_length=200, verbose_name="Nom complet")
    founded_year = models.PositiveIntegerField(
        verbose_name="Année de fondation",
        validators=[MinValueValidator(1900), MaxValueValidator(2100)]
    )
    slogan = models.CharField(max_length=200, blank=True)
    description = models.TextField(verbose_name="Description")
    vision = models.TextField(verbose_name="Vision")
    
    # Localisation
    address = models.CharField(max_length=255, verbose_name="Adresse")
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='communities')
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Contact
    phone = models.CharField(max_length=20, verbose_name="Téléphone")
    email = models.EmailField(verbose_name="Email")
    website = models.URLField(blank=True, null=True, verbose_name="Site web")
    
    # Statistiques
    members_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de membres")
    leaders_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de leaders")
    weekly_services_count = models.PositiveIntegerField(default=0, verbose_name="Services hebdomadaires")
    baptisms_current_year = models.PositiveIntegerField(default=0, verbose_name="Baptêmes année courante")
    
    # État
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    class Meta:
        verbose_name = "Communauté"
        verbose_name_plural = "Communautés"
        ordering = ['founded_year', 'name']
    
    def __str__(self):
        return self.full_name


class Pastor(TimeStampedModel):
    """Modèle pour les pasteurs"""
    # Informations personnelles
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    title = models.CharField(max_length=100, verbose_name="Titre")
    
    # Contact
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    # Profil
    bio = models.TextField(verbose_name="Biographie")
    experience_years = models.PositiveIntegerField(verbose_name="Années d'expérience")
    image = models.ImageField(upload_to='pastors/', null=True, blank=True)
    image_url = models.URLField(blank=True, null=True, help_text="URL externe pour l'image")
    
    # Relations
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='pastors')
    is_principal = models.BooleanField(default=False, verbose_name="Pasteur principal")
    
    class Meta:
        verbose_name = "Pasteur"
        verbose_name_plural = "Pasteurs"
        ordering = ['-is_principal', 'last_name', 'first_name']
    
    def __str__(self):
        return f"{self.title} {self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Service(TimeStampedModel):
    """Modèle pour les services religieux"""
    DAYS_OF_WEEK = [
        (1, 'Lundi'),
        (2, 'Mardi'),
        (3, 'Mercredi'),
        (4, 'Jeudi'),
        (5, 'Vendredi'),
        (6, 'Samedi'),
        (7, 'Dimanche'),
    ]
    
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='services')
    day = models.PositiveSmallIntegerField(choices=DAYS_OF_WEEK, verbose_name="Jour")
    time = models.TimeField(verbose_name="Heure")
    type = models.CharField(max_length=100, verbose_name="Type de service")
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"
        ordering = ['day', 'time']
        unique_together = ['community', 'day', 'time']
    
    def __str__(self):
        return f"{self.get_day_display()} {self.time} - {self.type}"


class Ministry(TimeStampedModel):
    """Modèle pour les ministères"""
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='ministries')
    name = models.CharField(max_length=100, verbose_name="Nom")
    description = models.TextField()
    leader = models.ForeignKey('Leader', on_delete=models.SET_NULL, null=True, related_name='ministries_led')
    participants_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de participants")
    meeting_time = models.CharField(max_length=100, blank=True, verbose_name="Horaire de réunion")
    
    class Meta:
        verbose_name = "Ministère"
        verbose_name_plural = "Ministères"
        unique_together = ['community', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.community.name}"


class MinistryActivity(models.Model):
    """Modèle pour les activités d'un ministère"""
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, related_name='activities')
    name = models.CharField(max_length=100, verbose_name="Activité")
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = "Activité de ministère"
        verbose_name_plural = "Activités de ministère"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Event(TimeStampedModel):
    """Modèle pour les événements"""
    EVENT_TYPES = [
        ('spiritual', 'Spirituel'),
        ('sacrament', 'Sacrement'),
        ('formation', 'Formation'),
        ('cultural', 'Culturel'),
        ('social', 'Social'),
        ('evangelization', 'Évangélisation'),
        ('other', 'Autre'),
    ]
    
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=200, verbose_name="Titre")
    date = models.DateField(verbose_name="Date")
    start_time = models.TimeField(verbose_name="Heure de début")
    end_time = models.TimeField(null=True, blank=True, verbose_name="Heure de fin")
    type = models.CharField(max_length=20, choices=EVENT_TYPES, verbose_name="Type")
    description = models.TextField()
    location = models.CharField(max_length=200, verbose_name="Lieu")
    organizer = models.CharField(max_length=100, verbose_name="Organisateur")
    
    # Champs supplémentaires
    is_recurring = models.BooleanField(default=False, verbose_name="Récurrent")
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    registration_required = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        ordering = ['date', 'start_time']
    
    def __str__(self):
        return f"{self.title} - {self.date}"


class BibleStudy(TimeStampedModel):
    """Modèle pour les études bibliques"""
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='bible_studies')
    title = models.CharField(max_length=200, verbose_name="Titre")
    teacher = models.ForeignKey('Leader', on_delete=models.SET_NULL, null=True, related_name='bible_studies_taught')
    schedule = models.CharField(max_length=100, verbose_name="Horaire")
    duration_weeks = models.PositiveIntegerField(verbose_name="Durée en semaines")
    participants_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de participants")
    description = models.TextField()
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(null=True, blank=True, verbose_name="Date de fin")
    is_active = models.BooleanField(default=True, verbose_name="En cours")
    
    class Meta:
        verbose_name = "Étude biblique"
        verbose_name_plural = "Études bibliques"
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.title} - {self.community.name}"


class ReadingProgram(TimeStampedModel):
    """Modèle pour les programmes de lecture"""
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='reading_programs')
    title = models.CharField(max_length=200, verbose_name="Titre")
    participants_count = models.PositiveIntegerField(default=0, verbose_name="Participants")
    progress_percentage = models.PositiveIntegerField(
        default=0, 
        validators=[MaxValueValidator(100)],
        verbose_name="Progression (%)"
    )
    current_book = models.CharField(max_length=100, verbose_name="Livre actuel")
    weekly_reading = models.CharField(max_length=200, verbose_name="Lecture hebdomadaire")
    coordinator = models.ForeignKey('Leader', on_delete=models.SET_NULL, null=True, related_name='reading_programs')
    next_milestone = models.CharField(max_length=200, blank=True, verbose_name="Prochaine étape")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    class Meta:
        verbose_name = "Programme de lecture"
        verbose_name_plural = "Programmes de lecture"
    
    def __str__(self):
        return f"{self.title} - {self.community.name}"


class Meditation(TimeStampedModel):
    """Modèle pour les méditations"""
    MEDITATION_TYPES = [
        ('daily', 'Méditation quotidienne'),
        ('weekly', 'Réflexion hebdomadaire'),
        ('youth', 'Méditation jeunesse'),
        ('community', 'Méditation communautaire'),
        ('professional', 'Méditation professionnelle'),
        ('artistic', 'Méditation artistique'),
        ('student', 'Méditation étudiante'),
    ]
    
    CATEGORIES = [
        ('encouragement', 'Encouragement'),
        ('christian_life', 'Vie chrétienne'),
        ('relationships', 'Relations'),
        ('community', 'Communauté'),
        ('creativity', 'Créativité'),
        ('work', 'Travail'),
        ('wisdom', 'Sagesse'),
        ('faith', 'Foi'),
    ]
    
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='meditations')
    title = models.CharField(max_length=200, verbose_name="Titre")
    author = models.ForeignKey('Leader', on_delete=models.SET_NULL, null=True, related_name='meditations')
    bible_verse = models.CharField(max_length=100, verbose_name="Verset biblique")
    type = models.CharField(max_length=20, choices=MEDITATION_TYPES, verbose_name="Type")
    category = models.CharField(max_length=20, choices=CATEGORIES, verbose_name="Catégorie")
    content = models.TextField(verbose_name="Contenu")
    duration_minutes = models.PositiveIntegerField(verbose_name="Durée (minutes)")
    published_date = models.DateField(default=timezone.now)
    is_published = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Méditation"
        verbose_name_plural = "Méditations"
        ordering = ['-published_date']
    
    def __str__(self):
        return f"{self.title} - {self.author}"


class Leader(TimeStampedModel):
    """Modèle pour les leaders"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    position = models.CharField(max_length=100, verbose_name="Position")
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='leaders')
    experience_years = models.PositiveIntegerField(verbose_name="Années d'expérience")
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Leader"
        verbose_name_plural = "Leaders"
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.position}"


class LeaderSpecialty(models.Model):
    """Modèle pour les spécialités des leaders"""
    leader = models.ForeignKey(Leader, on_delete=models.CASCADE, related_name='specialties')
    name = models.CharField(max_length=100, verbose_name="Spécialité")
    
    class Meta:
        verbose_name = "Spécialité de leader"
        verbose_name_plural = "Spécialités de leader"
    
    def __str__(self):
        return self.name


class Baptism(TimeStampedModel):
    """Modèle pour les baptêmes"""
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='baptisms')
    date = models.DateField(verbose_name="Date")
    time = models.TimeField(verbose_name="Heure")
    location = models.CharField(max_length=200, verbose_name="Lieu")
    candidates_count = models.PositiveIntegerField(verbose_name="Nombre de candidats")
    preparation_sessions = models.PositiveIntegerField(verbose_name="Sessions de préparation")
    coordinator = models.ForeignKey(Leader, on_delete=models.SET_NULL, null=True, related_name='baptisms_coordinated')
    is_completed = models.BooleanField(default=False, verbose_name="Effectué")
    
    class Meta:
        verbose_name = "Baptême"
        verbose_name_plural = "Baptêmes"
        ordering = ['-date']
    
    def __str__(self):
        return f"Baptême {self.community.name} - {self.date}"


class BaptismRequirement(models.Model):
    """Modèle pour les exigences de baptême"""
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='baptism_requirements')
    requirement = models.CharField(max_length=255, verbose_name="Exigence")
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = "Exigence de baptême"
        verbose_name_plural = "Exigences de baptême"
        ordering = ['order']
    
    def __str__(self):
        return self.requirement


class BaptismStatistics(models.Model):
    """Modèle pour les statistiques de baptême"""
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='baptism_statistics')
    year = models.PositiveIntegerField(verbose_name="Année")
    count = models.PositiveIntegerField(verbose_name="Nombre")
    
    class Meta:
        verbose_name = "Statistique de baptême"
        verbose_name_plural = "Statistiques de baptême"
        unique_together = ['community', 'year']
        ordering = ['-year']
    
    def __str__(self):
        return f"{self.community.name} - {self.year}: {self.count} baptêmes"


class Testimony(TimeStampedModel):
    """Modèle pour les témoignages"""
    CATEGORIES = [
        ('healing', 'Guérison'),
        ('provision', 'Provision'),
        ('salvation', 'Salut'),
        ('deliverance', 'Délivrance'),
        ('relationship', 'Relations'),
        ('professional', 'Professionnel'),
        ('other', 'Autre'),
    ]
    
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='testimonies')
    author_name = models.CharField(max_length=100, verbose_name="Auteur")
    title = models.CharField(max_length=200, verbose_name="Titre")
    category = models.CharField(max_length=20, choices=CATEGORIES, verbose_name="Catégorie")
    excerpt = models.TextField(verbose_name="Extrait", max_length=500)
    full_content = models.TextField(verbose_name="Contenu complet")
    date = models.DateField(default=timezone.now)
    is_published = models.BooleanField(default=False, verbose_name="Publié")
    is_verified = models.BooleanField(default=False, verbose_name="Vérifié")
    
    class Meta:
        verbose_name = "Témoignage"
        verbose_name_plural = "Témoignages"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.title} - {self.author_name}"


class Gallery(TimeStampedModel):
    """Modèle pour les galeries photos"""
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='galleries')
    title = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='galleries/', null=True, blank=True)
    cover_image_url = models.URLField(blank=True, null=True)
    images_count = models.PositiveIntegerField(default=0, verbose_name="Nombre d'images")
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name='galleries')
    is_public = models.BooleanField(default=True, verbose_name="Publique")
    
    class Meta:
        verbose_name = "Galerie"
        verbose_name_plural = "Galeries"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.community.name}"


class GalleryImage(models.Model):
    """Modèle pour les images d'une galerie"""
    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='gallery_images/')
    image_url = models.URLField(blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Image de galerie"
        verbose_name_plural = "Images de galerie"
        ordering = ['order', '-uploaded_at']
    
    def __str__(self):
        return f"Image {self.id} - {self.gallery.title}"


# Modèles pour les membres et participation
class Member(TimeStampedModel):
    """Modèle pour les membres de la communauté"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Relations
    community = models.ForeignKey(Community, on_delete=models.PROTECT, related_name='members')
    baptism = models.ForeignKey(Baptism, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Statut
    is_active = models.BooleanField(default=True)
    join_date = models.DateField(default=timezone.now)
    
    class Meta:
        verbose_name = "Membre"
        verbose_name_plural = "Membres"
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class MemberMinistryParticipation(TimeStampedModel):
    """Modèle pour la participation des membres aux ministères"""
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='ministry_participations')
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, related_name='member_participations')
    role = models.CharField(max_length=100, blank=True, verbose_name="Rôle")
    join_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Participation au ministère"
        verbose_name_plural = "Participations aux ministères"
        unique_together = ['member', 'ministry']
    
    def __str__(self):
        return f"{self.member} - {self.ministry}"


class EventRegistration(TimeStampedModel):
    """Modèle pour les inscriptions aux événements"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='event_registrations')
    registration_date = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False, verbose_name="A participé")
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Inscription à l'événement"
        verbose_name_plural = "Inscriptions aux événements"
        unique_together = ['event', 'member']
    
    def __str__(self):
        return f"{self.member} - {self.event}"