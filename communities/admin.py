from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.urls import path
from django.template.response import TemplateResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import date, timedelta
import json

from .models import (
    Country, City, Community, Pastor, Service, Ministry, MinistryActivity,
    Event, BibleStudy, ReadingProgram, Meditation, Leader, LeaderSpecialty,
    Baptism, BaptismRequirement, BaptismStatistics, Testimony, Gallery,
    GalleryImage, Member, MemberMinistryParticipation, EventRegistration
)

# Personnalisation du site admin
admin.site.site_header = "⛪ Assemblée Évangélique - Administration"
admin.site.site_title = "Assemblée Évangélique"
admin.site.index_title = "Tableau de Bord"


# Classe de base pour un meilleur affichage
class BaseAdmin(admin.ModelAdmin):
    """Classe de base avec des styles personnalisés"""
    
    def colored_status(self, obj):
        """Affiche un statut coloré"""
        if hasattr(obj, 'is_active'):
            if obj.is_active:
                return format_html(
                    '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">Actif</span>'
                )
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">Inactif</span>'
            )
        return '-'
    colored_status.short_description = 'Statut'


# Inlines personnalisés
class ServiceInline(admin.TabularInline):
    model = Service
    extra = 0
    fields = ['day', 'time', 'type', 'description']
    
    class Media:
        css = {
            'all': ('admin/css/custom_inline.css',)
        }


class MinistryActivityInline(admin.TabularInline):
    model = MinistryActivity
    extra = 0
    fields = ['name', 'description', 'order']


class GalleryImageInline(admin.StackedInline):
    model = GalleryImage
    extra = 0
    fields = ['image_preview', 'image', 'image_url', 'caption', 'order']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 200px; border-radius: 5px;"/>',
                obj.image.url
            )
        elif obj.image_url:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 200px; border-radius: 5px;"/>',
                obj.image_url
            )
        return "Aucune image"
    image_preview.short_description = "Aperçu"


@admin.register(Community)
class CommunityAdmin(BaseAdmin):
    list_display = [
        'community_card', 'stats_display', 'location_display', 
        'colored_status', 'quick_actions'
    ]
    list_filter = ['is_active', 'city', 'founded_year']
    search_fields = ['name', 'full_name', 'slogan']
    readonly_fields = ['created_at', 'updated_at', 'map_preview', 'statistics_chart']
    inlines = [ServiceInline]
    
    fieldsets = (
        ('🏛️ Informations Principales', {
            'fields': ('slug', 'name', 'full_name', 'founded_year', 'slogan', 'is_active'),
            'classes': ('wide',)
        }),
        ('📝 Description', {
            'fields': ('description', 'vision'),
            'classes': ('collapse',)
        }),
        ('📍 Localisation', {
            'fields': ('address', 'city', 'latitude', 'longitude', 'map_preview'),
            'classes': ('wide',)
        }),
        ('📞 Contact', {
            'fields': ('phone', 'email', 'website'),
            'classes': ('wide',)
        }),
        ('📊 Statistiques', {
            'fields': (
                'members_count', 'leaders_count', 
                'weekly_services_count', 'baptisms_current_year',
                'statistics_chart'
            ),
            'classes': ('wide',)
        }),
        ('⏰ Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def community_card(self, obj):
        return format_html(
            '<div style="display: flex; align-items: center;">'
            '<div style="margin-right: 15px;">'
            '<div style="width: 50px; height: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
            'border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-size: 20px;">⛪</div>'
            '</div>'
            '<div>'
            '<strong style="font-size: 14px; color: #2c3e50;">{}</strong><br/>'
            '<span style="color: #7f8c8d; font-size: 12px;">Fondée en {}</span><br/>'
            '<span style="color: #95a5a6; font-size: 11px; font-style: italic;">{}</span>'
            '</div>'
            '</div>',
            obj.full_name, obj.founded_year, obj.slogan
        )
    community_card.short_description = "Communauté"
    
    def stats_display(self, obj):
        return format_html(
            '<div style="display: flex; gap: 10px; flex-wrap: wrap;">'
            '<span style="background: #e3f2fd; color: #1976d2; padding: 4px 8px; border-radius: 4px; font-size: 11px;">👥 {} membres</span>'
            '<span style="background: #f3e5f5; color: #7b1fa2; padding: 4px 8px; border-radius: 4px; font-size: 11px;">👔 {} leaders</span>'
            '<span style="background: #e8f5e9; color: #388e3c; padding: 4px 8px; border-radius: 4px; font-size: 11px;">🏛️ {} ministères</span>'
            '<span style="background: #fff3e0; color: #f57c00; padding: 4px 8px; border-radius: 4px; font-size: 11px;">💧 {} baptêmes</span>'
            '</div>',
            obj.members_count, obj.leaders_count, 
            obj.ministries.count(), obj.baptisms_current_year
        )
    stats_display.short_description = "Statistiques"
    
    def location_display(self, obj):
        return format_html(
            '<div style="background: #f8f9fa; padding: 8px; border-radius: 5px; border-left: 3px solid #6c757d;">'
            '<strong style="color: #495057;">📍 {}</strong><br/>'
            '<span style="color: #6c757d; font-size: 12px;">{}, {}</span>'
            '</div>',
            obj.address, obj.city.name, obj.city.country.name
        )
    location_display.short_description = "Localisation"
    
    def quick_actions(self, obj):
        return format_html(
            '<div style="display: flex; gap: 5px;">'
            '<a href="/admin/communities/event/?community__id={}" class="button" style="padding: 5px 10px; font-size: 11px;">📅 Événements</a>'
            '<a href="/admin/communities/ministry/?community__id={}" class="button" style="padding: 5px 10px; font-size: 11px;">🏛️ Ministères</a>'
            '<a href="/admin/communities/member/?community__id={}" class="button" style="padding: 5px 10px; font-size: 11px;">👥 Membres</a>'
            '</div>',
            obj.id, obj.id, obj.id
        )
    quick_actions.short_description = "Actions rapides"
    
    def map_preview(self, obj):
        if obj.latitude and obj.longitude:
            from decimal import Decimal
            # Convertir en float pour les calculs
            lat = float(obj.latitude)
            lng = float(obj.longitude)
            return format_html(
                '<div style="margin-top: 10px;">'
                '<iframe width="100%" height="300" frameborder="0" style="border:0; border-radius: 8px;" '
                'src="https://www.openstreetmap.org/export/embed.html?bbox={},{},{},{}&layer=mapnik&marker={},{}" '
                'allowfullscreen></iframe>'
                '</div>',
                lng - 0.01, lat - 0.01,
                lng + 0.01, lat + 0.01,
                lat, lng
            )
        return "Coordonnées non disponibles"
    map_preview.short_description = "Carte"
    
    def statistics_chart(self, obj):
        # Données pour le graphique
        data = {
            'labels': ['Membres', 'Leaders', 'Ministères', 'Services/sem', 'Baptêmes'],
            'values': [
                obj.members_count,
                obj.leaders_count,
                obj.ministries.count(),
                obj.weekly_services_count,
                obj.baptisms_current_year
            ]
        }
        
        return format_html(
            '<div style="margin-top: 15px; background: #f8f9fa; padding: 15px; border-radius: 8px;">'
            '<canvas id="stats-chart-{}" width="400" height="200"></canvas>'
            '<script>'
            'document.addEventListener("DOMContentLoaded", function() {{'
            '  var ctx = document.getElementById("stats-chart-{}").getContext("2d");'
            '  new Chart(ctx, {{'
            '    type: "bar",'
            '    data: {{'
            '      labels: {},'
            '      datasets: [{{'
            '        label: "Statistiques",'
            '        data: {},'
            '        backgroundColor: ['
            '          "rgba(54, 162, 235, 0.5)",'
            '          "rgba(255, 99, 132, 0.5)",'
            '          "rgba(255, 206, 86, 0.5)",'
            '          "rgba(75, 192, 192, 0.5)",'
            '          "rgba(153, 102, 255, 0.5)"'
            '        ],'
            '        borderColor: ['
            '          "rgba(54, 162, 235, 1)",'
            '          "rgba(255, 99, 132, 1)",'
            '          "rgba(255, 206, 86, 1)",'
            '          "rgba(75, 192, 192, 1)",'
            '          "rgba(153, 102, 255, 1)"'
            '        ],'
            '        borderWidth: 1'
            '      }}]'
            '    }},'
            '    options: {{'
            '      responsive: true,'
            '      maintainAspectRatio: false,'
            '      scales: {{'
            '        y: {{'
            '          beginAtZero: true'
            '        }}'
            '      }}'
            '    }}'
            '  }});'
            '}});'
            '</script>'
            '</div>',
            obj.id, obj.id, json.dumps(data['labels']), json.dumps(data['values'])
        )
    statistics_chart.short_description = "Graphique des statistiques"
    
    class Media:
        js = ('https://cdn.jsdelivr.net/npm/chart.js',)
        css = {
            'all': ('admin/css/custom_admin.css',)
        }


@admin.register(Pastor)
class PastorAdmin(BaseAdmin):
    list_display = ['pastor_profile', 'contact_info', 'community_badge', 'experience_badge']
    list_filter = ['is_principal', 'community', 'experience_years']
    search_fields = ['first_name', 'last_name', 'bio']
    readonly_fields = ['created_at', 'updated_at', 'image_display']
    
    fieldsets = (
        ('👤 Informations Personnelles', {
            'fields': ('first_name', 'last_name', 'title', 'is_principal'),
            'classes': ('wide',)
        }),
        ('📞 Contact', {
            'fields': ('phone', 'email'),
            'classes': ('wide',)
        }),
        ('📋 Profil', {
            'fields': ('bio', 'experience_years', 'image', 'image_url', 'image_display'),
            'classes': ('wide',)
        }),
        ('⛪ Affectation', {
            'fields': ('community',),
            'classes': ('wide',)
        }),
        ('⏰ Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def pastor_profile(self, obj):
        image = ""
        if obj.image:
            image = f'<img src="{obj.image.url}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover; margin-right: 15px;"/>'
        elif obj.image_url:
            image = f'<img src="{obj.image_url}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover; margin-right: 15px;"/>'
        else:
            image = '<div style="width: 50px; height: 50px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; color: white; margin-right: 15px;">👤</div>'
        
        principal_badge = ""
        if obj.is_principal:
            principal_badge = '<span style="background: #ffd700; color: #000; padding: 2px 6px; border-radius: 3px; font-size: 10px; margin-left: 8px;">⭐ Principal</span>'
        
        return format_html(
            '<div style="display: flex; align-items: center;">'
            '{}'
            '<div>'
            '<strong style="font-size: 14px; color: #2c3e50;">{}</strong>{}<br/>'
            '<span style="color: #7f8c8d; font-size: 12px;">{}</span>'
            '</div>'
            '</div>',
            image, obj.full_name, principal_badge, obj.title
        )
    pastor_profile.short_description = "Pasteur"
    
    def contact_info(self, obj):
        return format_html(
            '<div style="background: #f8f9fa; padding: 8px; border-radius: 5px;">'
            '📞 <a href="tel:{}">{}</a><br/>'
            '✉️ <a href="mailto:{}">{}</a>'
            '</div>',
            obj.phone, obj.phone or "Non renseigné",
            obj.email, obj.email or "Non renseigné"
        )
    contact_info.short_description = "Contact"
    
    def community_badge(self, obj):
        return format_html(
            '<span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px;">'
            '⛪ {}'
            '</span>',
            obj.community.name
        )
    community_badge.short_description = "Communauté"
    
    def experience_badge(self, obj):
        color = "#28a745" if obj.experience_years >= 10 else "#ffc107" if obj.experience_years >= 5 else "#17a2b8"
        return format_html(
            '<div style="text-align: center;">'
            '<div style="background: {}; color: white; padding: 8px; border-radius: 5px; font-size: 16px; font-weight: bold;">{}</div>'
            '<span style="color: #6c757d; font-size: 11px;">ans d\'expérience</span>'
            '</div>',
            color, obj.experience_years
        )
    experience_badge.short_description = "Expérience"
    
    def image_display(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 200px; max-width: 200px; border-radius: 10px;"/>',
                obj.image.url
            )
        elif obj.image_url:
            return format_html(
                '<img src="{}" style="max-height: 200px; max-width: 200px; border-radius: 10px;"/>',
                obj.image_url
            )
        return "Aucune image"
    image_display.short_description = "Photo"


@admin.register(Event)
class EventAdmin(BaseAdmin):
    list_display = ['event_card', 'date_time_display', 'type_badge', 'community_badge', 'registration_status']
    list_filter = ['type', 'community', 'date', 'registration_required']
    search_fields = ['title', 'description', 'organizer']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at', 'countdown_display']
    
    fieldsets = (
        ('📅 Informations de l\'Événement', {
            'fields': ('community', 'title', 'type', 'description'),
            'classes': ('wide',)
        }),
        ('⏰ Date et Horaire', {
            'fields': ('date', 'start_time', 'end_time', 'countdown_display'),
            'classes': ('wide',)
        }),
        ('📍 Lieu et Organisation', {
            'fields': ('location', 'organizer', 'is_recurring'),
            'classes': ('wide',)
        }),
        ('👥 Inscription', {
            'fields': ('registration_required', 'max_participants'),
            'classes': ('wide',)
        }),
        ('⏰ Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def event_card(self, obj):
        icon_map = {
            'spiritual': '🙏',
            'sacrament': '💧',
            'formation': '📚',
            'cultural': '🎭',
            'social': '🤝',
            'evangelization': '📢',
            'other': '📌'
        }
        icon = icon_map.get(obj.type, '📌')
        
        days_until = (obj.date - date.today()).days
        urgency_color = "#dc3545" if days_until <= 3 else "#ffc107" if days_until <= 7 else "#28a745"
        
        return format_html(
            '<div style="display: flex; align-items: center;">'
            '<div style="margin-right: 15px; font-size: 30px;">{}</div>'
            '<div>'
            '<strong style="font-size: 14px; color: #2c3e50;">{}</strong><br/>'
            '<span style="color: #7f8c8d; font-size: 12px;">Organisé par: {}</span><br/>'
            '<span style="background: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">Dans {} jours</span>'
            '</div>'
            '</div>',
            icon, obj.title, obj.organizer, urgency_color, days_until
        )
    event_card.short_description = "Événement"
    
    def date_time_display(self, obj):
        return format_html(
            '<div style="background: #f8f9fa; padding: 10px; border-radius: 5px; text-align: center;">'
            '<div style="font-size: 16px; font-weight: bold; color: #2c3e50;">📅 {}</div>'
            '<div style="color: #6c757d; margin-top: 5px;">🕐 {} - {}</div>'
            '<div style="color: #95a5a6; font-size: 11px; margin-top: 5px;">📍 {}</div>'
            '</div>',
            obj.date.strftime("%d %b %Y"),
            obj.start_time.strftime("%H:%M"),
            obj.end_time.strftime("%H:%M") if obj.end_time else "?",
            obj.location
        )
    date_time_display.short_description = "Date & Lieu"
    
    def type_badge(self, obj):
        color_map = {
            'spiritual': '#9c27b0',
            'sacrament': '#2196f3',
            'formation': '#ff9800',
            'cultural': '#e91e63',
            'social': '#4caf50',
            'evangelization': '#f44336',
            'other': '#607d8b'
        }
        color = color_map.get(obj.type, '#607d8b')
        
        return format_html(
            '<span style="background: {}; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px;">'
            '{}'
            '</span>',
            color, obj.get_type_display()
        )
    type_badge.short_description = "Type"
    
    def community_badge(self, obj):
        return format_html(
            '<span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px;">'
            '⛪ {}'
            '</span>',
            obj.community.name
        )
    community_badge.short_description = "Communauté"
    
    def registration_status(self, obj):
        if not obj.registration_required:
            return format_html(
                '<span style="background: #e0e0e0; color: #666; padding: 5px 10px; border-radius: 5px; font-size: 11px;">Libre</span>'
            )
        
        registered = obj.registrations.count()
        max_participants = obj.max_participants or "∞"
        percentage = (registered / obj.max_participants * 100) if obj.max_participants else 0
        color = "#dc3545" if percentage >= 90 else "#ffc107" if percentage >= 70 else "#28a745"
        
        return format_html(
            '<div style="background: #f8f9fa; padding: 8px; border-radius: 5px;">'
            '<div style="font-size: 12px; color: #495057; margin-bottom: 5px;">Inscrits: {}/{}</div>'
            '<div style="background: #e0e0e0; border-radius: 10px; height: 10px; overflow: hidden;">'
            '<div style="background: {}; height: 100%; width: {}%; transition: width 0.3s;"></div>'
            '</div>'
            '</div>',
            registered, max_participants, color, percentage
        )
    registration_status.short_description = "Inscriptions"
    
    def countdown_display(self, obj):
        days_until = (obj.date - date.today()).days
        
        if days_until < 0:
            return format_html(
                '<div style="background: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; text-align: center;">'
                '⏰ Événement passé il y a {} jours'
                '</div>',
                abs(days_until)
            )
        elif days_until == 0:
            return format_html(
                '<div style="background: #fff3cd; color: #856404; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;">'
                '🎉 C\'est aujourd\'hui!'
                '</div>'
            )
        else:
            return format_html(
                '<div style="background: #d4edda; color: #155724; padding: 10px; border-radius: 5px; text-align: center;">'
                '⏳ Dans {} jours'
                '</div>',
                days_until
            )
    countdown_display.short_description = "Compte à rebours"


@admin.register(Member)
class MemberAdmin(BaseAdmin):
    list_display = ['member_profile', 'contact_display', 'community_info', 'membership_status', 'participation_display']
    list_filter = ['is_active', 'community', 'join_date']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    date_hierarchy = 'join_date'
    readonly_fields = ['created_at', 'updated_at', 'member_timeline']
    
    fieldsets = (
        ('👤 Informations Personnelles', {
            'fields': ('user', 'first_name', 'last_name', 'date_of_birth'),
            'classes': ('wide',)
        }),
        ('📞 Contact', {
            'fields': ('email', 'phone'),
            'classes': ('wide',)
        }),
        ('⛪ Affiliation', {
            'fields': ('community', 'baptism', 'join_date', 'is_active'),
            'classes': ('wide',)
        }),
        ('📊 Historique', {
            'fields': ('member_timeline',),
            'classes': ('wide',)
        }),
        ('⏰ Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def member_profile(self, obj):
        avatar_color = "#" + str(hash(obj.email))[-6:]
        initials = f"{obj.first_name[0]}{obj.last_name[0]}".upper()
        
        return format_html(
            '<div style="display: flex; align-items: center;">'
            '<div style="width: 40px; height: 40px; border-radius: 50%; background: {}; '
            'display: flex; align-items: center; justify-content: center; color: white; '
            'font-weight: bold; margin-right: 12px;">{}</div>'
            '<div>'
            '<strong style="font-size: 14px; color: #2c3e50;">{} {}</strong><br/>'
            '<span style="color: #95a5a6; font-size: 11px;">Membre depuis {}</span>'
            '</div>'
            '</div>',
            avatar_color, initials, obj.first_name, obj.last_name, 
            obj.join_date.strftime("%b %Y")
        )
    member_profile.short_description = "Membre"
    
    def contact_display(self, obj):
        return format_html(
            '<div style="font-size: 12px;">'
            '📧 <a href="mailto:{}">{}</a><br/>'
            '📱 <a href="tel:{}">{}</a>'
            '</div>',
            obj.email, obj.email[:25] + "..." if len(obj.email) > 25 else obj.email,
            obj.phone, obj.phone or "Non renseigné"
        )
    contact_display.short_description = "Contact"
    
    def community_info(self, obj):
        return format_html(
            '<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
            'color: white; padding: 8px 12px; border-radius: 8px; text-align: center;">'
            '<div style="font-size: 12px; opacity: 0.9;">⛪</div>'
            '<div style="font-weight: bold; font-size: 13px;">{}</div>'
            '</div>',
            obj.community.name
        )
    community_info.short_description = "Communauté"
    
    def membership_status(self, obj):
        if obj.is_active:
            days_member = (date.today() - obj.join_date).days
            years = days_member // 365
            months = (days_member % 365) // 30
            
            if obj.baptism:
                baptism_badge = '<span style="background: #2196f3; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; margin-left: 5px;">💧 Baptisé</span>'
            else:
                baptism_badge = ""
            
            return format_html(
                '<div>'
                '<span style="background: #28a745; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px;">✓ Actif</span>'
                '{}'
                '<div style="color: #6c757d; font-size: 11px; margin-top: 5px;">{} ans {} mois</div>'
                '</div>',
                baptism_badge, years, months
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px;">✗ Inactif</span>'
        )
    membership_status.short_description = "Statut"
    
    def participation_display(self, obj):
        ministries_count = obj.ministry_participations.filter(is_active=True).count()
        events_count = obj.event_registrations.count()
        
        return format_html(
            '<div style="display: flex; gap: 8px;">'
            '<span style="background: #e8f5e9; color: #388e3c; padding: 4px 8px; border-radius: 4px; font-size: 11px;">🏛️ {} ministère(s)</span>'
            '<span style="background: #fff3e0; color: #f57c00; padding: 4px 8px; border-radius: 4px; font-size: 11px;">📅 {} événement(s)</span>'
            '</div>',
            ministries_count, events_count
        )
    participation_display.short_description = "Participation"
    
    def member_timeline(self, obj):
        # Timeline des activités du membre
        events = []
        
        # Date d'inscription
        events.append({
            'date': obj.join_date,
            'type': 'join',
            'title': 'Inscription',
            'icon': '🎉',
            'color': '#28a745'
        })
        
        # Baptême
        if obj.baptism:
            events.append({
                'date': obj.baptism.date,
                'type': 'baptism',
                'title': 'Baptême',
                'icon': '💧',
                'color': '#2196f3'
            })
        
        # Participations aux ministères
        for participation in obj.ministry_participations.all()[:3]:
            events.append({
                'date': participation.join_date,
                'type': 'ministry',
                'title': f'Rejoint {participation.ministry.name}',
                'icon': '🏛️',
                'color': '#9c27b0'
            })
        
        # Trier par date
        events.sort(key=lambda x: x['date'], reverse=True)
        
        timeline_html = '<div style="padding: 15px; background: #f8f9fa; border-radius: 8px;">'
        timeline_html += '<h4 style="margin-top: 0;">📅 Historique du membre</h4>'
        
        for event in events[:5]:
            timeline_html += format_html(
                '<div style="display: flex; align-items: center; margin-bottom: 10px; padding: 10px; background: white; border-radius: 5px; border-left: 3px solid {};">'
                '<div style="font-size: 20px; margin-right: 10px;">{}</div>'
                '<div style="flex-grow: 1;">'
                '<strong>{}</strong><br/>'
                '<span style="color: #6c757d; font-size: 11px;">{}</span>'
                '</div>'
                '</div>',
                event['color'], event['icon'], event['title'], 
                event['date'].strftime("%d %b %Y")
            )
        
        timeline_html += '</div>'
        return mark_safe(timeline_html)
    member_timeline.short_description = "Chronologie"


# Vue personnalisée pour le tableau de bord
def admin_dashboard_view(request):
    context = {
        'title': 'Tableau de Bord',
        'communities': Community.objects.all(),
        'total_members': Member.objects.filter(is_active=True).count(),
        'upcoming_events': Event.objects.filter(date__gte=date.today()).order_by('date')[:5],
        'recent_baptisms': Baptism.objects.filter(is_completed=False).order_by('date')[:5],
        'stats': {
            'communities': Community.objects.count(),
            'total_members': Community.objects.aggregate(Sum('members_count'))['members_count__sum'] or 0,
            'total_ministries': Ministry.objects.count(),
            'upcoming_events': Event.objects.filter(date__gte=date.today()).count(),
        }
    }
    return TemplateResponse(request, 'admin/dashboard.html', context)


# Personnalisation de l'admin index
admin.site.index_template = 'admin/custom_index.html'