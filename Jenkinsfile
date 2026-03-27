pipeline {
    agent any

    environment {
        SMTP_EMAIL = credentials('smtp-email')
        SMTP_PASSWORD = credentials('smtp-password')
    }

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
                // The tests will now have access to SMTP_EMAIL and SMTP_PASSWORD
                bat 'pytest test_auth.py'
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
