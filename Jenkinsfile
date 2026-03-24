pipeline {
    agent any

    stages {
        stage('Setup') {
            steps {
                echo 'Setting up environment...'
                bat 'pip install -r requirements.txt'
            }
        }
        stage('Test') {
            steps {
                echo 'Running tests...'
                bat 'pytest test_app.py'
            }
        }
        stage('Run') {
            steps {
                echo 'Starting the application...'
                // Note: In a real Jenkins environment, we wouldn't just run app.py like this
                // as it blocks the pipeline. This is for demonstration.
                echo 'App is ready to be deployed.'
            }
        }
    }
}
