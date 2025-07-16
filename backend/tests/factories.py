import factory
from datetime import datetime
from app.db.models.project import User, Project, IFCModel, Conflict, Solution, SolutionFeedback
from app.auth.auth import get_password_hash


class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    id = factory.Sequence(lambda n: n)
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    hashed_password = factory.LazyAttribute(lambda obj: get_password_hash("testpassword"))
    full_name = factory.Faker('name')
    is_active = True
    is_superuser = False
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class ProjectFactory(factory.Factory):
    class Meta:
        model = Project
    
    id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: f"Test Project {n}")
    description = factory.Faker('text', max_nb_chars=200)
    status = "created"
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    owner_id = factory.SubFactory(UserFactory)


class IFCModelFactory(factory.Factory):
    class Meta:
        model = IFCModel
    
    id = factory.Sequence(lambda n: n)
    filename = factory.Sequence(lambda n: f"test_model_{n}.ifc")
    file_path = factory.Sequence(lambda n: f"/tmp/test_model_{n}.ifc")
    status = "uploaded"
    created_at = factory.LazyFunction(datetime.utcnow)
    project_id = factory.SubFactory(ProjectFactory)


class ConflictFactory(factory.Factory):
    class Meta:
        model = Conflict
    
    id = factory.Sequence(lambda n: n)
    conflict_type = factory.Iterator(["collision", "clearance", "structural"])
    severity = factory.Iterator(["high", "medium", "low"])
    description = factory.Faker('text', max_nb_chars=200)
    status = "detected"
    created_at = factory.LazyFunction(datetime.utcnow)
    project_id = factory.SubFactory(ProjectFactory)


class SolutionFactory(factory.Factory):
    class Meta:
        model = Solution
    
    id = factory.Sequence(lambda n: n)
    solution_type = factory.Iterator(["redesign", "relocate", "material_change"])
    description = factory.Faker('text', max_nb_chars=200)
    estimated_cost = factory.Faker('random_int', min=1000, max=50000)  # in cents
    estimated_time = factory.Faker('random_int', min=1, max=30)  # in days
    confidence_score = factory.Faker('random_int', min=60, max=100)
    status = "proposed"
    created_at = factory.LazyFunction(datetime.utcnow)
    conflict_id = factory.SubFactory(ConflictFactory)


class SolutionFeedbackFactory(factory.Factory):
    class Meta:
        model = SolutionFeedback
    
    id = factory.Sequence(lambda n: n)
    feedback_type = factory.Iterator(["selected_suggested", "custom_solution"])
    custom_solution_description = factory.Faker('text', max_nb_chars=300)
    implementation_notes = factory.Faker('text', max_nb_chars=200)
    effectiveness_rating = factory.Faker('random_int', min=1, max=5)
    created_at = factory.LazyFunction(datetime.utcnow)
    conflict_id = factory.SubFactory(ConflictFactory)
    solution_id = factory.SubFactory(SolutionFactory)
    user_id = factory.SubFactory(UserFactory)


# Helper functions for creating test data
def create_user(db_session, **kwargs):
    """Create a user in the database"""
    user_data = UserFactory.build(**kwargs)
    user = User(**user_data.__dict__)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_project(db_session, owner=None, **kwargs):
    """Create a project in the database"""
    if owner is None:
        owner = create_user(db_session)
    
    project_data = ProjectFactory.build(owner_id=owner.id, **kwargs)
    project = Project(**project_data.__dict__)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def create_conflict(db_session, project=None, **kwargs):
    """Create a conflict in the database"""
    if project is None:
        project = create_project(db_session)
    
    conflict_data = ConflictFactory.build(project_id=project.id, **kwargs)
    conflict = Conflict(**conflict_data.__dict__)
    db_session.add(conflict)
    db_session.commit()
    db_session.refresh(conflict)
    return conflict


def create_solution(db_session, conflict=None, **kwargs):
    """Create a solution in the database"""
    if conflict is None:
        conflict = create_conflict(db_session)
    
    solution_data = SolutionFactory.build(conflict_id=conflict.id, **kwargs)
    solution = Solution(**solution_data.__dict__)
    db_session.add(solution)
    db_session.commit()
    db_session.refresh(solution)
    return solution