from functools import wraps
from dotenv import load_dotenv
import os

from flask import Flask, request, render_template, redirect, session, jsonify
from Project_utils import SQLiteDatabase, get_schedule_slots

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return func(*args, **kwargs)

    return wrapper


@app.get('/')
def index():
    return render_template('index.html', title='Главная')


@app.route('/register', methods=['GET', 'POST'])
def get_register_page():
    if request.method == 'GET':
        return render_template('register.html', title='Регистрация')
    else:
        with SQLiteDatabase('base.db') as db:
            form_data = request.form
            user_name = form_data.get('username')
            password = form_data.get('password')
            birthday = form_data.get('birthday')
            phone = form_data.get('phone')
            db.insert('users', {'login': user_name, 'password': password, 'birth_date': birthday, 'phone': phone})

        return 'Registration success'


@app.route('/login', methods=['GET', 'POST'])
def get_login_page():
    if request.method == 'GET':
        if 'user' in session:
            return redirect('/user')
        return render_template('login.html', title='Авторизация')
    else:
        form_data = request.form
        user_name = form_data.get('username')
        password = form_data.get('password')
        with SQLiteDatabase('base.db') as db:
            user = db.select(table_name='users', method='fetchone',
                             conditions={'login': user_name, 'password': password})
            if user:
                session['user'] = user
                return redirect('/user')
            else:
                return 'Login failed'


@app.route('/logout')
@login_required
def get_logout_page():
    session.pop('user', None)
    return redirect('/')


@app.route('/user', methods=['GET', 'POST'])
@login_required
def get_user_page():
    if request.method == 'GET':
        user = session.get('user')
        return render_template('user.html', title='Личный кабинет', user=user)
    if request.method == 'POST':
        return 'User created'


@app.route('/user/<int:user_id>/funds', methods=['GET', 'POST'])
@login_required
def get_funds_page(user_id):
    if request.method == 'GET':
        with SQLiteDatabase('base.db') as db:
            funds = db.select(table_name='users', method='fetchall', columns=['funds'], conditions={'id': user_id})
            return funds
    if request.method == 'POST':
        return 'Add something to funds'


@app.route('/user/reservations', methods=['GET', 'POST'])
@login_required
def get_reservations_page():
    user = session.get('user')
    if request.method == 'GET':
        with SQLiteDatabase('base.db') as db:
            reservations = db.select(table_name='reservations', method='fetchall', conditions={'user_id': user['id']},
                                     columns=['reservations.id AS reservation_id', 'reservations.date',
                                              'reservations.time', 'services.duration',
                                              'services.name AS service_name', 'trainers.name AS trainer_name', 'fitness_centers.name AS fitness_center_name'],
                                     join_conditions={'services': {'reservations.service_id': 'services.id'},
                                                      'trainers': {'reservations.trainer_id': 'trainers.id'},
                                                      'fitness_centers': {'trainers.fitness_center_id': 'fitness_centers.id'}})
            services = db.select(table_name='services', method='fetchall')
            return render_template('reservations.html', title='Мои бронирования', reservations=reservations,
                                   services=services)
    if request.method == 'POST':
        form_data = request.form
        service_id = form_data.get('service_id')
        trainer_id = form_data.get('trainer_id')
        date = form_data.get('date')
        time = form_data.get('time')
        with SQLiteDatabase('base.db') as db:
            db.insert('reservations', {'user_id': user['id'], 'service_id': service_id, 'date': date, 'time': time, 'trainer_id': trainer_id})
        return redirect('/user/reservations')


@app.route('/user/reservations/<int:reservation_id>', methods=['GET', 'POST'])
@login_required
def get_reservation_page(reservation_id):
    if request.method == 'GET':
        with SQLiteDatabase('base.db') as db:
            reservation = db.select(table_name='reservations', method='fetchone', conditions={'id': reservation_id})
            if not reservation:
                return 'Reservation not found'
            return reservation
    if request.method == 'POST':
        return 'Reservation created'


@app.route('/user/checkout', methods=['GET', 'POST'])
@login_required
def get_checkout_page():
    if request.method == 'GET':
        return 'Checkout page'
    if request.method == 'POST':
        return 'Checkout created'


@app.get('/fitness_centers')
def get_fitness_center_page():
    with SQLiteDatabase('base.db') as db:
        fitness_centers = db.select(table_name='fitness_centers', method='fetchall')
        if not fitness_centers:
            return 'Fitness centers not found'
        return render_template('fitness_centers.html', title='Фитнес центры', fitness_centers=fitness_centers)


@app.get('/fitness_center/<int:fitness_center_id>')
def get_fitness_center_id_page(fitness_center_id):
    with SQLiteDatabase('base.db') as db:
        fitness_center = db.select(table_name='fitness_centers', method='fetchone',
                                   conditions={'id': fitness_center_id})
        if not fitness_center:
            return 'Fitness center not found'
        return fitness_center


@app.get('/fitness_center/<int:fitness_center_id>/trainers')
def get_trainer_page(fitness_center_id):
    with SQLiteDatabase('base.db') as db:
        trainers = db.select(table_name='trainers', method='fetchall',
                             conditions={'trainers.fitness_center_id': fitness_center_id},
                             columns=['trainers.id', 'trainers.name AS trainer_name', 'trainers.age', 'trainers.gender',
                                      'fitness_centers.name AS fitness_center_name', 'trainers.fitness_center_id'],
                             join_conditions={'fitness_centers': {'trainers.fitness_center_id': 'fitness_centers.id'}})
        if not trainers:
            return 'Trainers not found'
        return render_template('trainers.html', title='Тренеры', trainers=trainers)


@app.route('/fitness_center/<int:fitness_center_id>/trainers/<int:trainer_id>/<int:service_id>',
           methods=['GET', 'POST'])
def get_trainer_service_page(fitness_center_id, trainer_id, service_id):
    with SQLiteDatabase('base.db') as db:
        trainer = db.select(table_name='trainers', method='fetchone',
                            conditions={'trainers.fitness_center_id': fitness_center_id, 'trainers.id': trainer_id},
                            columns=['trainers.id', 'trainers.name AS trainer_name', 'trainers.age',
                                     'trainers.gender',
                                     'fitness_centers.name AS fitness_center_name'],
                            join_conditions={
                                'fitness_centers': {'trainers.fitness_center_id': 'fitness_centers.id'}})
        trainer_schedule = db.select(table_name='trainer_schedule', method='fetchall',
                                     conditions={'trainer_id': trainer_id})
    if request.method == 'GET':
        return render_template('trainer_page.html', title=f'{trainer["trainer_name"]}', trainer=trainer,
                               trainer_schedule=trainer_schedule)
    if request.method == 'POST':
        form_data = request.form
        date = form_data.get('date')
        available_time = get_schedule_slots(trainer_id, service_id, date)
        return render_template('trainer_page.html', title=f'{trainer["trainer_name"]}', trainer=trainer,
                        trainer_schedule=trainer_schedule, available_time=available_time, service_id=service_id)


@app.route('/fitness_center/<int:fitness_center_id>/trainers/<int:trainer_id>/rating', methods=['GET', 'POST'])
@login_required
def get_trainer_rating_page(fitness_center_id, trainer_id):
    with SQLiteDatabase('base.db') as db:
        user = session.get('user')
        user_review = db.select(table_name='reviews', method='fetchone',
                                conditions={'trainer_id': trainer_id, 'user_id': user['id']})
        if request.method == 'GET':
            rating = db.select(table_name='reviews', method='fetchall',
                               conditions={'trainer_id': trainer_id, 'fitness_center_id': fitness_center_id},
                               columns=['trainers.name AS trainer_name', 'reviews.points', 'reviews.id',
                                        'reviews.text', 'reviews.id AS review_id', 'users.login AS user_name'],
                               join_conditions={'trainers': {'reviews.trainer_id': 'trainers.id'},
                                                'users': {'reviews.user_id': 'users.id'}}
                               )
            trainer = db.select(table_name='trainers', method='fetchone', conditions={'id': trainer_id})
            return render_template('rating.html', title='Рейтинг', rating=rating, fitness_center_id=fitness_center_id,
                                   trainer=trainer, user_review=user_review)
        if request.method == 'POST':
            form_data = request.form
            points = form_data.get('points')
            text = form_data.get('text')
            if user_review:
                db.update('reviews', {'points': points, 'text': text},
                          {'trainer_id': trainer_id, 'user_id': user['id']})
                return redirect(f'/fitness_center/{fitness_center_id}/trainers/{trainer_id}/rating')
            else:
                db.commit('reviews', {'trainer_id': trainer_id, 'user_id': user['id'], 'points': points, 'text': text})
                return redirect(f'/fitness_center/{fitness_center_id}/trainers/{trainer_id}/rating')


@app.get('/fitness_center/<int:fitness_center_id>/services')
@login_required
def get_services_page(fitness_center_id):
    user = session.get('user')
    trainer_services = {}
    with SQLiteDatabase('base.db') as db:
        services = db.select(table_name='services', method='fetchall',
                             conditions={'fitness_services.fitness_center_id': fitness_center_id},
                             columns=['services.id AS service_id', 'services.name AS service_name',
                                      'services.price', 'services.max_attendees',
                                      'services.duration', 'services.description',
                                      'fitness_centers.name AS fitness_center_name',
                                      'fitness_centers.id AS fitness_center_id'],
                             join_conditions={
                                 'fitness_services': {'service_id': 'services.id'},
                                 'fitness_centers': {'fitness_centers.id': 'fitness_services.fitness_center_id'}
                             })
        trainers = db.select(table_name='trainers', method='fetchall',
                             columns=['trainers.id AS trainer_id', 'trainers.name AS trainer_name', 'trainers.age',
                                      'trainers.gender', 'trainer_services.service_id AS service_id'],
                             conditions={'trainers.fitness_center_id': fitness_center_id},
                             join_conditions={'trainer_services': {'trainer_id': 'trainers.id'}})
        for trainer in trainers:
            if trainer['service_id'] not in trainer_services:
                trainer_services[trainer['service_id']] = {}
            trainer_services[trainer['service_id']][trainer['trainer_id']] = trainer['trainer_name']
        return render_template('services.html', title='Услуги', services=services, trainer_services=trainer_services)


@app.route('/fitness_center/<int:fitness_center_id>/services/<int:service_id>', methods=['GET', 'POST'])
def get_service_id_page(fitness_center_id, service_id):
    if request.method == 'GET':
        with SQLiteDatabase('base.db') as db:
            service = db.select(table_name='services', method='fetchone',
                                conditions={'fitness_center_id': fitness_center_id, 'services.id': service_id},
                                columns=['services.id AS service_id', 'services.name AS service_name', 'services.price',
                                         'services.duration', 'fitness_centers.name AS fitness_center_name'],
                                join_conditions={'fitness_services': {'service_id': 'services.id'},
                                                 'fitness_centers': {
                                                     'fitness_centers.id': 'fitness_services.fitness_center_id'}})
            if not service:
                return 'Service not found'
            return service


@app.route('/fitness_center/<int:fitness_center_id>/loyalty_program', methods=['GET', 'POST'])
def get_loyalty_program_page(fitness_center_id):
    if request.method == 'GET':
        return f'Welcome to the list of the loyalty programs! Fitness center id: {fitness_center_id}'
    if request.method == 'POST':
        return f'Loyalty program created! Fitness center id: {fitness_center_id}'
    if request.method == 'PUT':
        return f'Loyalty program updated! Fitness center id: {fitness_center_id}'


if __name__ == '__main__':
    app.run()
