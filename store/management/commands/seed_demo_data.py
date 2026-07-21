from datetime import timedelta
from decimal import Decimal
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Profile
from amc.models import AMCContract, AMCVisit
from boq.models import ProjectBOQ, ProjectBOQItem
from complaints.models import CustomerComplaint
from customers.models import Customer, CustomerServiceSchedule
from material_issue.models import MaterialIssue, MaterialIssueItem
from projects.models import CustomerProject
from service.models import ServiceComplaint
from store.models import (
    StoreCategory,
    StoreItem,
    StoreTransaction,
    Zone,
    InventoryUnit,
    UnitStatusEvent,
    InstallationJob,
    WarrantyRegistration,
    ScrapReturnRecord,
    ScrapReturnEvent,
)


D = Decimal


class Command(BaseCommand):
    help = "Reset this copy and seed it with fictional demo data for an AC service company."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="Confirm wiping existing records in this database.")

    @transaction.atomic
    def handle(self, *args, **options):
        self.assert_demo_environment()
        if not options["yes"]:
            raise CommandError("This command resets the demo database. Re-run with --yes inside puriaccooling-demo.")

        self.stdout.write("Clearing demo database...")
        self.clear_data()

        today = timezone.localdate()
        ceo = User.objects.create_superuser(
            username="demo_ceo",
            email="owner.demo@example.com",
            password="Demo@12345",
            first_name="Demo",
            last_name="Owner",
        )
        manager = User.objects.create_user(
            username="demo_manager",
            email="manager.demo@example.com",
            password="Demo@12345",
            first_name="Service",
            last_name="Manager",
            is_staff=True,
        )
        Profile.objects.create(user=ceo, role="CEO")
        Profile.objects.create(user=manager, role="MANAGER")
        technicians = self.create_technicians()

        customers = self.create_customers(today, manager)
        projects = self.create_projects(today, customers, manager)
        categories, items = self.create_store(manager)
        boqs = self.create_boqs(projects, items, ceo, manager)
        self.create_material_issues(projects, boqs, items, manager)
        self.create_services(today, customers, manager)
        self.create_amc(today, customers, manager)
        self.create_general_transactions(projects, items, manager)
        self.create_unit_tracking_demo(today, items, customers, technicians, manager)
        self.create_scrap_loss_demo(today, customers, projects, technicians, manager, ceo)
        self.shape_service_schedules(today)

        self.stdout.write(self.style.SUCCESS("Demo database seeded successfully."))
        self.stdout.write("Demo login: demo_ceo / Demo@12345 or demo_manager / Demo@12345")
        self.stdout.write(
            f"Created {Customer.objects.count()} customers, {CustomerProject.objects.count()} projects, "
            f"{ProjectBOQ.objects.count()} BOQs, {MaterialIssue.objects.count()} material issues, "
            f"{StoreItem.objects.count()} store items, {StoreTransaction.objects.count()} transactions, "
            f"{InventoryUnit.objects.count()} serial units, {ScrapReturnRecord.objects.count()} scrap return records."
        )

    def create_technicians(self):
        technicians = {}
        for username, first, last in [
            ("tech_rahul", "Rahul", "Singh"),
            ("tech_sana", "Sana", "Khan"),
            ("tech_imran", "Imran", "Ali"),
        ]:
            technicians[username] = User.objects.create_user(
                username=username,
                email=f"{username}@demo.example.com",
                password="Demo@12345",
                first_name=first,
                last_name=last,
                is_staff=True,
            )
        return technicians


    def assert_demo_environment(self):
        if os.getenv("DEMO_RESET_CONFIRM") == "allow":
            return

        base_dir = str(settings.BASE_DIR)
        db_name = str(settings.DATABASES["default"].get("NAME", ""))
        if not base_dir.endswith("puriaccooling-demo") or "puriaccooling-demo" not in db_name:
            raise CommandError(
                "Refusing to reset data because this is not the puriaccooling-demo project/database. "
                "Set DEMO_RESET_CONFIRM=allow only for the standalone demo deployment."
            )

    def clear_data(self):
        for model in [
            ScrapReturnEvent,
            ScrapReturnRecord,
            WarrantyRegistration,
            InstallationJob,
            UnitStatusEvent,
            InventoryUnit,
            Zone,
            MaterialIssueItem,
            MaterialIssue,
            StoreTransaction,
            ProjectBOQItem,
            ProjectBOQ,
            AMCVisit,
            AMCContract,
            ServiceComplaint,
            CustomerComplaint,
            CustomerServiceSchedule,
            CustomerProject,
            StoreItem,
            StoreCategory,
            Customer,
            Profile,
            User,
        ]:
            model.objects.all().delete()

    def create_customers(self, today, user):
        specs = [
            ("Aarav Sharma", "", "WARRANTY", "9000000101", "aarav.demo@example.com", "A-42, Green Park", "Delhi", "Delhi", today - timedelta(days=110), None),
            ("Green Valley Residency", "Green Valley RWA", "AMC", "9000000102", "facility.greenvalley@example.com", "Tower 3, Sector 56", "Gurugram", "Haryana", None, today - timedelta(days=260)),
            ("Northstar Business Park", "Northstar Facilities Pvt Ltd", "AMC", "9000000103", "ops.northstar@example.com", "Plot 18, Sector 62", "Noida", "Uttar Pradesh", None, today - timedelta(days=210)),
            ("Maya Kapoor", "", "GENERAL", "9000000104", "maya.demo@example.com", "C-119, Malviya Nagar", "Jaipur", "Rajasthan", None, None),
            ("Bluebay Hotel", "Bluebay Hospitality LLP", "AMC", "9000000105", "maintenance.bluebay@example.com", "Lake Road, Sector 17", "Chandigarh", "Chandigarh", None, today - timedelta(days=300)),
            ("MetroCare Clinic", "MetroCare Health Services", "WARRANTY", "9000000106", "admin.metrocare@example.com", "Model Town", "Ludhiana", "Punjab", today - timedelta(days=80), None),
            ("Rohan Mehta", "", "GENERAL", "9000000107", "rohan.demo@example.com", "B-22, Vaishali", "Ghaziabad", "Uttar Pradesh", None, None),
            ("Summit Mall", "Summit Retail Spaces", "AMC", "9000000108", "facility.summit@example.com", "MG Road", "Pune", "Maharashtra", None, today - timedelta(days=40)),
            ("Prisha Verma", "", "WARRANTY", "9000000109", "prisha.demo@example.com", "Civil Lines", "Amritsar", "Punjab", today - timedelta(days=25), None),
            ("Orchid Foods Factory", "Orchid Foods Pvt Ltd", "GENERAL", "9000000110", "plant.orchid@example.com", "Industrial Area Phase 2", "Mohali", "Punjab", None, None),
            ("Skyline Corporate Suites", "Skyline Workspaces", "AMC", "9000000111", "admin.skyline@example.com", "Cyber City", "Gurugram", "Haryana", None, today - timedelta(days=335)),
            ("Nisha Bansal", "", "GENERAL", "9000000112", "nisha.demo@example.com", "Sector 21", "Chandigarh", "Chandigarh", None, None),
        ]
        customers = {}
        for name, company, category, phone, email, address, city, state, warranty_start, amc_start in specs:
            customer = Customer.objects.create(
                customer_category=category,
                customer_name=name,
                company_name=company or None,
                phone_number=phone,
                whatsapp_number=phone,
                email=email,
                gst_number="27ABCDE1234F1Z5" if company else None,
                address=address,
                landmark="Demo landmark",
                city=city,
                state=state,
                pincode="110001",
                warranty_start_date=warranty_start,
                amc_start_date=amc_start,
                remarks="Fictional demo customer for presentation use.",
                created_by=user,
            )
            customers[name] = customer
        return customers

    def create_projects(self, today, customers, user):
        specs = [
            ("Northstar Business Park", "VRV retrofit - Block A", "Noida Sector 62", "ONGOING", "96", "HP", "1850000", today - timedelta(days=45), today + timedelta(days=25)),
            ("Green Valley Residency", "Residential tower split AC installation", "Gurugram Sector 56", "INSTALLATION", "42", "TR", "720000", today - timedelta(days=20), today + timedelta(days=12)),
            ("Bluebay Hotel", "Banquet hall ductable AC upgrade", "Chandigarh", "TESTING", "60", "TR", "1180000", today - timedelta(days=60), today + timedelta(days=5)),
            ("MetroCare Clinic", "Clinic HVAC expansion", "Ludhiana", "COMMISSIONED", "28", "TR", "640000", today - timedelta(days=90), today - timedelta(days=8)),
            ("Orchid Foods Factory", "Cold room service and AC controls", "Mohali Industrial Area", "MATERIAL_REQUIRED", "35", "TR", "860000", today - timedelta(days=8), today + timedelta(days=30)),
            ("Summit Mall", "Food court cassette AC replacement", "Pune MG Road", "PLANNING", "72", "TR", "1420000", today + timedelta(days=5), today + timedelta(days=50)),
        ]
        projects = {}
        for customer_name, site, location, status, cap, unit, value, start, end in specs:
            project = CustomerProject.objects.create(
                customer=customers[customer_name],
                site_name=site,
                location=location,
                site_address=f"{site}, {location}",
                capacity_value=D(cap),
                capacity_unit=unit,
                project_value=D(value),
                start_date=start,
                expected_completion_date=end,
                actual_completion_date=(today - timedelta(days=8) if status == "COMMISSIONED" else None),
                project_status=status,
                material_consumed_notes="Demo material consumption tracked through BOQ and issue slips.",
                material_collection_notes="Pending material collection is visible in project reports.",
                project_stage_notes="Fictional project workflow for client demo.",
                remarks="Demo AC installation project.",
                insurance_start_date=start,
                insurance_end_date=end + timedelta(days=365),
                created_by=user,
            )
            projects[site] = project
        return projects

    def create_store(self, user):
        categories = {}
        for name in ["Copper & Refrigerant Piping", "Indoor AC Units", "Outdoor AC Units", "Electrical & Controls", "Installation Consumables", "Service Spares", "Tools & Safety"]:
            categories[name] = StoreCategory.objects.create(category_name=name)

        specs = [
            ("Copper Pipe", "1/4 inch", "MTR", "220", "70", True, True, "Copper & Refrigerant Piping"),
            ("Copper Pipe", "1/2 inch", "MTR", "180", "60", True, True, "Copper & Refrigerant Piping"),
            ("Drain Pipe", "25 mm", "MTR", "300", "80", False, False, "Installation Consumables"),
            ("Insulation Tube", "13 mm", "MTR", "260", "75", False, False, "Installation Consumables"),
            ("Wall Mount Indoor Unit", "1.5 TR", "NOS", "18", "4", False, True, "Indoor AC Units"),
            ("Cassette Indoor Unit", "2.0 TR", "NOS", "10", "2", False, True, "Indoor AC Units"),
            ("VRV Indoor Unit", "2 HP", "NOS", "12", "3", True, False, "Indoor AC Units"),
            ("VRV Outdoor Unit", "12 HP", "NOS", "4", "1", True, False, "Outdoor AC Units"),
            ("Outdoor Condensing Unit", "3.0 TR", "NOS", "7", "2", False, True, "Outdoor AC Units"),
            ("MCB", "32 Amp", "NOS", "90", "20", False, False, "Electrical & Controls"),
            ("Copper Cable", "4 core", "MTR", "500", "120", False, False, "Electrical & Controls"),
            ("Remote Controller", "Universal", "NOS", "35", "8", False, False, "Service Spares"),
            ("Fan Motor", "Indoor", "NOS", "14", "3", False, False, "Service Spares"),
            ("Service Gas", "R32", "KG", "75", "20", False, False, "Service Spares"),
            ("Safety Harness", "Technician Kit", "NOS", "12", "2", False, False, "Tools & Safety"),
        ]
        items = {}
        for desc, size, unit, opening, minimum, vrv, non_vrv, category in specs:
            item = StoreItem.objects.create(
                category=categories[category],
                item_description=desc,
                size=size,
                serial_number=f"DEMO-{desc[:3].upper()}-{len(items)+1:03d}",
                remarks="Demo inventory item",
                is_vrv=vrv,
                is_non_vrv=non_vrv,
                unit=unit,
                opening_stock=D(opening),
                current_stock=D(opening),
                minimum_stock=D(minimum),
                alert_percentage=D("85"),
                created_by=user,
            )
            items[f"{desc} {size}"] = item
        return categories, items

    def create_boqs(self, projects, items, ceo, manager):
        plans = [
            ("VRV retrofit - Block A", "VRV system BOQ", "APPROVED", [("VRV Indoor Unit 2 HP", "9", "62000"), ("VRV Outdoor Unit 12 HP", "2", "410000"), ("Copper Pipe 1/2 inch", "120", "680"), ("Copper Cable 4 core", "160", "110"), ("Drain Pipe 25 mm", "90", "85")]),
            ("Residential tower split AC installation", "Apartment installation BOQ", "SUBMITTED", [("Wall Mount Indoor Unit 1.5 TR", "12", "38500"), ("Outdoor Condensing Unit 3.0 TR", "6", "72000"), ("Copper Pipe 1/4 inch", "90", "420"), ("Insulation Tube 13 mm", "100", "65"), ("MCB 32 Amp", "18", "450")]),
            ("Banquet hall ductable AC upgrade", "Hotel upgrade BOQ", "APPROVED", [("Cassette Indoor Unit 2.0 TR", "8", "78000"), ("Outdoor Condensing Unit 3.0 TR", "4", "72000"), ("Copper Pipe 1/2 inch", "80", "680"), ("Remote Controller Universal", "8", "1200")]),
            ("Clinic HVAC expansion", "Clinic commissioning BOQ", "CLOSED", [("Wall Mount Indoor Unit 1.5 TR", "6", "38500"), ("Copper Pipe 1/4 inch", "40", "420"), ("Service Gas R32", "8", "950"), ("Fan Motor Indoor", "2", "3200")]),
            ("Cold room service and AC controls", "Factory service BOQ", "DRAFT", [("Service Gas R32", "18", "950"), ("Fan Motor Indoor", "5", "3200"), ("MCB 32 Amp", "10", "450"), ("Safety Harness Technician Kit", "3", "2400")]),
        ]
        boqs = {}
        for site, title, status, lines in plans:
            boq = ProjectBOQ.objects.create(
                project=projects[site],
                title=title,
                status=status,
                remarks="Demo quotation/BOQ data for presentation.",
                created_by=manager,
                approved_by=ceo if status in {"APPROVED", "CLOSED"} else None,
            )
            for key, qty, rate in lines:
                ProjectBOQItem.objects.create(boq=boq, store_item=items[key], required_quantity=D(qty), rate=D(rate), remarks="Demo BOQ line")
            boqs[site] = boq
        return boqs

    def create_material_issues(self, projects, boqs, items, user):
        issue_specs = [
            ("VRV retrofit - Block A", "Material for VRV riser work", "Team Alpha", [("VRV Indoor Unit 2 HP", "4", "2"), ("Copper Pipe 1/2 inch", "55", "45"), ("Copper Cable 4 core", "60", "40")]),
            ("Residential tower split AC installation", "Apartment wing material", "Team Bravo", [("Wall Mount Indoor Unit 1.5 TR", "4", "1"), ("Copper Pipe 1/4 inch", "32", "20"), ("MCB 32 Amp", "8", "6")]),
            ("Banquet hall ductable AC upgrade", "Testing and finishing material", "Team Delta", [("Cassette Indoor Unit 2.0 TR", "3", "2"), ("Remote Controller Universal", "3", "1"), ("Copper Pipe 1/2 inch", "24", "18")]),
        ]
        for site, heading, team, lines in issue_specs:
            issue = MaterialIssue.objects.create(project=projects[site], boq=boqs[site], heading=heading, issued_to=team, received_by=f"{team} Lead", status="ISSUED", remarks="Demo issue slip", issued_by=user)
            boq_items = {line.store_item_id: line for line in boqs[site].items.all()}
            for key, issued, consumed in lines:
                MaterialIssueItem.objects.create(material_issue=issue, store_item=items[key], boq_item=boq_items.get(items[key].id), issued_quantity=D(issued), consumed_quantity=D(consumed), remarks="Demo issued material")

        general_issue = MaterialIssue.objects.create(project=None, boq=None, heading="Emergency service material", issued_to="Service Team", received_by="Service Coordinator", status="ISSUED", remarks="Demo material issue without project", issued_by=user)
        MaterialIssueItem.objects.create(material_issue=general_issue, store_item=items["Service Gas R32"], issued_quantity=D("5"), consumed_quantity=D("3"), remarks="Allowed issue without project for quick repair")

    def create_services(self, today, customers, user):
        specs = [
            ("Maya Kapoor", "AC not cooling properly; gas pressure check required", "PENDING", None, "Technician Rahul"),
            ("Aarav Sharma", "First free warranty service and filter cleaning", "IN_PROGRESS", None, "Technician Sana"),
            ("Northstar Business Park", "Server room cassette AC water leakage", "COMPLETED", today - timedelta(days=1), "Team Alpha"),
            ("Rohan Mehta", "Remote not working and indoor unit display blinking", "COMPLETED", today - timedelta(days=4), "Technician Imran"),
            ("Bluebay Hotel", "Banquet hall cooling imbalance", "HOLD", None, "Team Delta"),
            ("Nisha Bansal", "Annual cleaning and drain line flush", "PENDING", None, "Technician Kavya"),
        ]
        for name, complaint, status, completed, tech in specs:
            cust = customers[name]
            ServiceComplaint.objects.create(
                complaint_date=today - timedelta(days=2 if status != "PENDING" else 0),
                customer=cust,
                customer_address=cust.address,
                contact_number=cust.phone_number,
                nature_of_complaint=complaint,
                technician_name=tech,
                status=status,
                service_completed_date=completed,
                remarks="Demo repair/maintenance booking.",
                created_by=user,
            )
            CustomerComplaint.objects.create(
                customer=cust,
                visit_date=today - timedelta(days=1),
                no_of_technicians=2,
                complaint_title=complaint[:120],
                complaint_description=complaint,
                work_done="Demo service notes recorded in customer history." if completed else "",
                status="COMPLETED" if status == "COMPLETED" else "PENDING",
                remarks="Demo customer service history.",
            )

    def create_amc(self, today, customers, user):
        for name, value, tech in [
            ("Green Valley Residency", "96000", "Team Bravo"),
            ("Northstar Business Park", "180000", "Team Alpha"),
            ("Bluebay Hotel", "144000", "Team Delta"),
            ("Summit Mall", "210000", "Team Gamma"),
            ("Skyline Corporate Suites", "165000", "Team Alpha"),
        ]:
            contract = AMCContract.objects.create(
                customer=customers[name],
                contract_start_date=today - timedelta(days=210),
                contract_value=D(value),
                services_per_year=4,
                service_frequency="QUARTERLY",
                technician_name=tech,
                status="ACTIVE",
                remarks="Demo AMC contract with quarterly planned visits.",
                created_by=user,
            )
            for offset, status in [(75, "COMPLETED"), (150, "COMPLETED"), (225, "PENDING"), (300, "PENDING")]:
                visit_date = contract.contract_start_date + timedelta(days=offset)
                AMCVisit.objects.create(
                    amc=contract,
                    visit_date=visit_date,
                    technician_name=tech,
                    status=status,
                    work_done="Filter cleaning, drain check, gas pressure inspection." if status == "COMPLETED" else "",
                    customer_feedback="Satisfied with service" if status == "COMPLETED" else "",
                    next_visit_date=visit_date + timedelta(days=75),
                    remarks="Demo AMC visit schedule.",
                    created_by=user,
                )

    def create_general_transactions(self, projects, items, user):
        StoreTransaction.objects.create(item=items["Remote Controller Universal"], transaction_type="IN", purpose="PURCHASE", quantity=D("12"), issued_to="Demo Supplier", description="Demo purchase invoice INV-DEMO-1001", created_by=user)
        StoreTransaction.objects.create(item=items["Fan Motor Indoor"], transaction_type="OUT", purpose="SERVICE", quantity=D("1"), service_customer_name="Rohan Mehta", issued_to="Technician Imran", description="Demo service replacement", created_by=user)
        StoreTransaction.objects.create(item=items["Insulation Tube 13 mm"], transaction_type="OUT", purpose="PROJECT", project=projects["Residential tower split AC installation"], quantity=D("14"), issued_to="Team Bravo", description="Demo project material issue outside BOQ", created_by=user)


    def create_unit_tracking_demo(self, today, items, customers, technicians, user):
        zones = {
            "Row A": Zone.objects.create(name="Row A", warehouse_name="Main Warehouse", notes="Split and wall-mounted units"),
            "Row B": Zone.objects.create(name="Row B", warehouse_name="Main Warehouse", notes="Outdoor units"),
            "Yard 1": Zone.objects.create(name="Yard 1", warehouse_name="Main Warehouse", notes="Large VRV and ductable units"),
        }
        unit_specs = [
            ("Wall Mount Indoor Unit 1.5 TR", "DAI-WMI-26001", "IN_WAREHOUSE", "Row A", "tech_rahul", None, "Received sealed."),
            ("Wall Mount Indoor Unit 1.5 TR", "DAI-WMI-26002", "DISPATCHED", "Row A", "tech_rahul", "Aarav Sharma", "Dispatched for apartment installation."),
            ("Wall Mount Indoor Unit 1.5 TR", "VOLT-WMI-26003", "WITH_INSTALLATION_TEAM", None, "tech_sana", "Green Valley Residency", "With team for Tower 3."),
            ("Cassette Indoor Unit 2.0 TR", "HIT-CAS-26004", "INSTALLED", None, "tech_imran", "Bluebay Hotel", "Installed and tested."),
            ("VRV Indoor Unit 2 HP", "DAI-VRV-IN-26005", "IN_WAREHOUSE", "Yard 1", "tech_rahul", None, "Ready for dispatch."),
            ("VRV Outdoor Unit 12 HP", "DAI-VRV-OUT-26006", "WITH_INSTALLATION_TEAM", None, "tech_sana", "Northstar Business Park", "Handoff to installation team."),
            ("Outdoor Condensing Unit 3.0 TR", "VOLT-ODU-26007", "RETURNED_TO_WAREHOUSE", "Row B", "tech_imran", "MetroCare Clinic", "Returned due site readiness issue."),
            ("Outdoor Condensing Unit 3.0 TR", "HIT-ODU-26008", "DAMAGED", "Row B", "tech_rahul", None, "Outdoor casing dent found during movement."),
            ("VRV Indoor Unit 2 HP", "DAI-VRV-IN-26009", "MISSING", None, "tech_sana", "Northstar Business Park", "Not traceable after site handoff."),
            ("Cassette Indoor Unit 2.0 TR", "HIT-CAS-26010", "INSTALLED", None, "tech_imran", "Summit Mall", "Installed at food court."),
        ]
        for item_key, serial, status, zone_name, tech_key, customer_name, note in unit_specs:
            tech = technicians[tech_key]
            customer = customers.get(customer_name) if customer_name else None
            zone = zones.get(zone_name) if zone_name else None
            unit = InventoryUnit.objects.create(
                store_item=items[item_key],
                serial_number=serial,
                current_status="IN_WAREHOUSE",
                current_zone=zones.get("Row A"),
                current_handler=user,
                customer=customer,
                condition_note="Demo intake event.",
            )
            UnitStatusEvent.objects.create(unit=unit, status="IN_WAREHOUSE", zone=unit.current_zone, handler=user, condition_note="Demo intake event.")
            if status != "IN_WAREHOUSE":
                unit.current_status = status
                unit.current_zone = zone
                unit.current_handler = tech
                unit.customer = customer
                unit.condition_note = note
                unit.save(update_fields=["current_status", "current_zone", "current_handler", "customer", "condition_note", "updated_at"])
                UnitStatusEvent.objects.create(unit=unit, status=status, zone=zone, handler=tech, condition_note=note)
            if status in {"WITH_INSTALLATION_TEAM", "INSTALLED", "RETURNED_TO_WAREHOUSE"} and customer:
                job = InstallationJob.objects.create(
                    unit=unit,
                    customer=customer,
                    technician=tech,
                    scheduled_date=today - timedelta(days=6),
                    completed_date=today - timedelta(days=1) if status == "INSTALLED" else None,
                    status="INSTALLED" if status == "INSTALLED" else ("RETURNED" if status == "RETURNED_TO_WAREHOUSE" else "IN_PROGRESS"),
                    warranty_registered=status == "INSTALLED",
                    notes="Demo installation handoff record.",
                )
                if status == "INSTALLED":
                    WarrantyRegistration.objects.create(
                        installation_job=job,
                        customer_name=customer.customer_name,
                        customer_phone=customer.phone_number,
                        serial_number=serial,
                        brand=unit.store_item.category.category_name,
                        product=f"{unit.store_item.item_description} {unit.store_item.size or ''}".strip(),
                        install_date=job.completed_date,
                    )

    def create_scrap_loss_demo(self, today, customers, projects, technicians, user, ceo):
        specs = [
            ("Maya Kapoor", None, "tech_rahul", "Old indoor fan motor", "1", "0", "SCRAP", "1800", today - timedelta(days=3), "PENDING", "Pending old part return."),
            ("Aarav Sharma", None, "tech_sana", "Faulty remote controller", "2", "1", "REUSABLE", "450", today - timedelta(days=1), "PARTIALLY_RETURNED", "One remote returned, one pending."),
            ("Bluebay Hotel", "Banquet hall ductable AC upgrade", "tech_imran", "Damaged copper scrap bundle", "18", "18", "SCRAP", "220", today - timedelta(days=2), "RETURNED", "Returned to store."),
            ("Northstar Business Park", "VRV retrofit - Block A", "tech_sana", "Old PCB board", "1", "0", "LOST", "6500", today - timedelta(days=9), "LOST", "Marked lost after site audit."),
            ("Green Valley Residency", "Residential tower split AC installation", "tech_rahul", "Reusable drain pump", "1", "0", "REUSABLE", "3200", today - timedelta(days=12), "APPROVED_LOSS", "Approved as loss by owner."),
            ("Rohan Mehta", None, "tech_imran", "Old compressor shell", "1", "0", "SCRAP", "2800", today + timedelta(days=4), "PENDING", "Return due next week."),
        ]
        for customer_name, project_name, tech_key, item_name, expected, received, condition, value, due, status, remarks in specs:
            customer = customers[customer_name]
            project = projects.get(project_name) if project_name else None
            record = ScrapReturnRecord.objects.create(
                customer=customer,
                project=project,
                project_reference=project.site_name if project else customer.customer_name,
                complaint_or_job_reference="Demo service/job card",
                technician=technicians[tech_key],
                item_name=item_name,
                quantity_expected=D(expected),
                quantity_received=D(received),
                condition=condition,
                approx_value=D(value),
                due_return_date=due,
                status=status,
                remarks=remarks,
                approved_by=ceo if status in {"LOST", "APPROVED_LOSS"} else None,
                created_by=user,
            )
            ScrapReturnEvent.objects.create(scrap_return_record=record, event_type="CREATED", remarks="Demo scrap return expectation created.", logged_by=user)
            if D(received) > 0:
                event_type = "FULLY_RETURNED" if status == "RETURNED" else "PARTIAL_RETURN_LOGGED"
                ScrapReturnEvent.objects.create(scrap_return_record=record, event_type=event_type, quantity_logged=D(received), remarks="Demo return logged.", logged_by=user)
            if status == "LOST":
                ScrapReturnEvent.objects.create(scrap_return_record=record, event_type="MARKED_LOST", remarks=remarks, logged_by=ceo)
            if status == "APPROVED_LOSS":
                ScrapReturnEvent.objects.create(scrap_return_record=record, event_type="APPROVED_LOSS", remarks=remarks, logged_by=ceo)

    def shape_service_schedules(self, today):
        schedules = list(CustomerServiceSchedule.objects.select_related("customer").order_by("service_date"))
        for index, schedule in enumerate(schedules):
            if schedule.service_date < today - timedelta(days=25):
                schedule.status = "COMPLETED" if index % 3 else "MISSED"
                schedule.completed_date = schedule.service_date + timedelta(days=1) if schedule.status == "COMPLETED" else None
                schedule.remarks = "Demo historical service schedule."
            elif schedule.service_date <= today + timedelta(days=14):
                schedule.status = "PENDING"
                schedule.remarks = "Demo upcoming reminder."
            schedule.save(update_fields=["status", "completed_date", "remarks"])
