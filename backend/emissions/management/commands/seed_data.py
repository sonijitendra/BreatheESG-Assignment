from decimal import Decimal
from datetime import date
from django.core.management.base import BaseCommand
from core.models import Tenant
from ingestion.models import DataSource
from emissions.models import EmissionFactor

class Command(BaseCommand):
    help = 'Seeds multi-tenant demo data and standard 2024 DEFRA/GHG Protocol emission factors.'

    def handle(self, *args, **options):
        self.stdout.write("Starting data seeding process...")

        # 1. Create Tenant
        tenant, created = Tenant.objects.get_or_create(
            slug='acme-corp',
            defaults={
                'name': 'Acme Corp',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created Tenant: {tenant.name}"))
        else:
            self.stdout.write(f"Tenant {tenant.name} already exists.")

        # 2. Create Data Sources
        sources_to_create = [
            {
                'name': 'SAP Fuel Procurement',
                'source_type': DataSource.SourceType.SAP,
                'description': 'Ingest purchase orders of diesel, petrol, and natural gas from SAP EKPO/MSEG ALV exports.'
            },
            {
                'name': 'Utility Electricity Bills',
                'source_type': DataSource.SourceType.UTILITY,
                'description': 'Ingest facility electricity consumption bills downloaded from energy portals.'
            },
            {
                'name': 'Corporate Travel Analytics',
                'source_type': DataSource.SourceType.TRAVEL,
                'description': 'Ingest business travel expense and flight itinerary records from Concur/Navan.'
            }
        ]

        for s_data in sources_to_create:
            source, s_created = DataSource.objects.get_or_create(
                tenant=tenant,
                source_type=s_data['source_type'],
                defaults={
                    'name': s_data['name'],
                    'description': s_data['description'],
                    'is_active': True
                }
            )
            if s_created:
                self.stdout.write(self.style.SUCCESS(f"Created Data Source: {source.name}"))
            else:
                self.stdout.write(f"Data Source {source.name} already exists.")

        # 3. Seed Emission Factors
        # Clean up existing factors first to prevent duplicate primary keys or overlaps
        EmissionFactor.objects.filter(tenant__isnull=True).delete()
        self.stdout.write("Cleared existing default emission factors.")

        factors = [
            # Scope 1 — Fuels
            {
                'category': 'fuel',
                'subcategory': 'diesel',
                'scope': 1,
                'unit_numerator': 'kgCO2e',
                'unit_denominator': 'litre',
                'factor_value': Decimal('2.700000'),
                'source_reference': 'DEFRA 2024 (Fuels - Liquid Fuels)',
                'valid_from': date(2024, 1, 1),
                'region': 'UK'
            },
            {
                'category': 'fuel',
                'subcategory': 'petrol',
                'scope': 1,
                'unit_numerator': 'kgCO2e',
                'unit_denominator': 'litre',
                'factor_value': Decimal('2.310000'),
                'source_reference': 'DEFRA 2024 (Fuels - Liquid Fuels)',
                'valid_from': date(2024, 1, 1),
                'region': 'UK'
            },
            {
                'category': 'fuel',
                'subcategory': 'natural_gas',
                'scope': 1,
                'unit_numerator': 'kgCO2e',
                'unit_denominator': 'm3',
                'factor_value': Decimal('2.020000'),
                'source_reference': 'DEFRA 2024 (Fuels - Gaseous Fuels)',
                'valid_from': date(2024, 1, 1),
                'region': 'UK'
            },
            
            # Scope 2 — Grid Electricity
            {
                'category': 'electricity',
                'subcategory': 'grid_average',
                'scope': 2,
                'unit_numerator': 'kgCO2e',
                'unit_denominator': 'kWh',
                'factor_value': Decimal('0.207070'),
                'source_reference': 'DEFRA 2024 (UK Grid Average)',
                'valid_from': date(2024, 1, 1),
                'region': 'UK'
            },
            {
                'category': 'electricity',
                'subcategory': 'grid_average',
                'scope': 2,
                'unit_numerator': 'kgCO2e',
                'unit_denominator': 'kWh',
                'factor_value': Decimal('0.378740'),
                'source_reference': 'US EPA eGRID 2024 (US Grid Average)',
                'valid_from': date(2024, 1, 1),
                'region': 'US'
            },
            {
                'category': 'electricity',
                'subcategory': 'grid_average',
                'scope': 2,
                'unit_numerator': 'kgCO2e',
                'unit_denominator': 'kWh',
                'factor_value': Decimal('0.705000'),
                'source_reference': 'India CEA CO2 Baseline Database v19',
                'valid_from': date(2024, 1, 1),
                'region': 'India'
            },

            # Scope 3 — Flights
            {
                'category': 'travel_flight',
                'subcategory': 'short_haul_economy',
                'scope': 3,
                'unit_numerator': 'kgCO2e',
                'unit_denominator': 'passenger-km',
                'factor_value': Decimal('0.182870'),
                'source_reference': 'DEFRA 2024 (Flights - Domestic/Short-haul)',
                'valid_from': date(2024, 1, 1),
                'region': 'UK'
            },
            {
                'category': 'travel_flight',
                'subcategory': 'short_haul_business',
                'scope': 3,
                'unit_numerator': 'kgCO2e',
                'unit_denominator': 'passenger-km',
                'factor_value': Decimal('0.274300'),
                'source_reference': 'DEFRA 2024 (Flights - Short-haul Business)',
                'valid_from': date(2024, 1, 1),
                'region': 'UK'
            },
            {
                'category': 'travel_flight',
                'subcategory': 'long_haul_economy',
                'scope': 3,
                'unit_numerator': 'kgCO2e',
                'unit_denominator': 'passenger-km',
                'factor_value': Decimal('0.200110'),
                'source_reference': 'DEFRA 2024 (Flights - Long-haul Economy)',
                'valid_from': date(2024, 1, 1),
                'region': 'UK'
            },
            {
                'category': 'travel_flight',
                'subcategory': 'long_haul_business',
                'scope': 3,
                'unit_numerator': 'kgCO2e',
                'unit_denominator': 'passenger-km',
                'factor_value': Decimal('0.580280'),
                'source_reference': 'DEFRA 2024 (Flights - Long-haul Business)',
                'valid_from': date(2024, 1, 1),
                'region': 'UK'
            },

            # Scope 3 — Lodging & Other Travel
            {
                'category': 'travel_hotel',
                'subcategory': 'hotel_per_room_night',
                'scope': 3,
                'unit_numerator': 'kgCO2e',
                'unit_denominator': 'room-night',
                'factor_value': Decimal('15.900000'),
                'source_reference': 'DEFRA 2024 (Hotel Stays - UK)',
                'valid_from': date(2024, 1, 1),
                'region': 'UK'
            },
            {
                'category': 'travel_ground',
                'subcategory': 'taxi',
                'scope': 3,
                'unit_numerator': 'kgCO2e',
                'unit_denominator': 'km',
                'factor_value': Decimal('0.148800'),
                'source_reference': 'DEFRA 2024 (Business Travel - Land - Taxi)',
                'valid_from': date(2024, 1, 1),
                'region': 'UK'
            },
            {
                'category': 'travel_ground',
                'subcategory': 'rental_car_average',
                'scope': 3,
                'unit_numerator': 'kgCO2e',
                'unit_denominator': 'km',
                'factor_value': Decimal('0.171200'),
                'source_reference': 'DEFRA 2024 (Business Travel - Land - Average Car)',
                'valid_from': date(2024, 1, 1),
                'region': 'UK'
            },
            {
                'category': 'travel_ground',
                'subcategory': 'rail',
                'scope': 3,
                'unit_numerator': 'kgCO2e',
                'unit_denominator': 'passenger-km',
                'factor_value': Decimal('0.035460'),
                'source_reference': 'DEFRA 2024 (Business Travel - Land - Rail)',
                'valid_from': date(2024, 1, 1),
                'region': 'UK'
            },
        ]

        for f_data in factors:
            factor = EmissionFactor.objects.create(**f_data)
            self.stdout.write(
                f"Seeded Factor: {factor.category}/{factor.subcategory} = {factor.factor_value} ({factor.region})"
            )

        self.stdout.write(self.style.SUCCESS("Demo and Factor seeding complete! Ready for analyst review."))
