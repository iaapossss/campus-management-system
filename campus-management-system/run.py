from app import create_app, db
from app.models import generate_mock_data, Course

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Course.query.first():
            num_students, num_courses = generate_mock_data(app, db)
            print(f"Generated {num_students} students and {num_courses} courses.")
        else:
            print("Mock data already exists.")
    app.run(debug=True)


print("=== Registered Routes ===")
for rule in app.url_map.iter_rules():
    print(rule)
print("=========================")