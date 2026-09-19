"""Minimal setup screens for existing staff, tables and catalogue data."""

from django.contrib import admin

from .models import ComposicionPlato, Ingrediente, Mesa, Plato, Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rol", "cuenta_acceso")
    list_filter = ("rol",)


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ("numero",)


@admin.register(Ingrediente)
class IngredienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cantidad_disponible", "activo")


class ComposicionPlatoInline(admin.TabularInline):
    model = ComposicionPlato
    extra = 0


@admin.register(Plato)
class PlatoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio", "activo", "puntaje_carga_preparacion")
    inlines = [ComposicionPlatoInline]
