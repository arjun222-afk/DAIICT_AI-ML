document.addEventListener('DOMContentLoaded', function() {
    const startView = document.getElementById('start-view');
    const categoryView = document.getElementById('category-view');
    const quizView = document.getElementById('quiz-view');
    const resultsView = document.getElementById('results-view');
    const startButton = document.getElementById('start-quiz-btn');
    const categoryCards = document.querySelectorAll('.category-card');
    const questionText = document.getElementById('question-text');
    const optionsContainer = document.getElementById('options-container');
    const questionCounter = document.getElementById('question-counter');
    const quizProgress = document.getElementById('quiz-progress');
    const signupButton = document.getElementById('signup-btn');
    
    let currentCategory = '';
    let questions = [];
    let currentQuestionIndex = 0;
    let userAnswers = [];
    let startTime;
    
    startButton.addEventListener('click', () => {
        startView.style.display = 'none';
        categoryView.style.display = 'block';
    });
    
    categoryCards.forEach(card => {
        card.addEventListener('click', () => {
            currentCategory = card.dataset.category;
            fetchQuestions(currentCategory);
        });
    });
    
    signupButton.addEventListener('click', () => {
        window.location.href = '/signup';
    });
    
    function fetchQuestions(category) {
        fetch(`/api/quiz?category=${category}`)
            .then(response => response.json())
            .then(data => {
                questions = data;
                currentQuestionIndex = 0;
                userAnswers = [];
                startTime = new Date();
                startQuiz();
            })
            .catch(error => {
                console.error('Error fetching questions:', error);
                useMockData(category);
            });
    }
    
    function useMockData(category) {
        let mockQuestions;
        
        if (category === 'technical') {
            mockQuestions = [
                {
                    id: 1,
                    question: "Which language is primarily used for web front-end development?",
                    options: ["Python", "JavaScript", "Java", "C++"],
                    correctAnswer: "JavaScript",
                    skill: "front_end"
                },
                {
                    id: 2,
                    question: "What does SQL stand for?",
                    options: ["Structured Query Language", "Simple Question Language", "Standard Query Logic", "Sequential Query Loop"],
                    correctAnswer: "Structured Query Language",
                    skill: "database"
                },
                {
                    id: 3,
                    question: "Which of these is NOT a Python web framework?",
                    options: ["Django", "Flask", "FastAPI", "Express"],
                    correctAnswer: "Express",
                    skill: "back_end"
                },
                {
                    id: 4,
                    question: "Which data structure uses LIFO (Last In First Out)?",
                    options: ["Queue", "Stack", "Array", "Linked List"],
                    correctAnswer: "Stack",
                    skill: "data_structures"
                },
                {
                    id: 5,
                    question: "Which of these is a NoSQL database?",
                    options: ["PostgreSQL", "MySQL", "MongoDB", "Oracle"],
                    correctAnswer: "MongoDB",
                    skill: "database"
                }
            ];
        } else {
            mockQuestions = [
                {
                    id: 1,
                    question: "Which approach would be most effective when dealing with a disagreement in a team?",
                    options: ["Avoid the conflict altogether", "Listen to all perspectives and find a compromise", "Insist on your way if you believe it's right", "Let someone else make the decision"],
                    correctAnswer: "Listen to all perspectives and find a compromise",
                    skill: "conflict_resolution"
                },
                {
                    id: 2,
                    question: "What is the best way to handle receiving critical feedback?",
                    options: ["Defend your actions", "Ignore it if you disagree", "Listen, reflect, and respond constructively", "Immediately implement all suggestions"],
                    correctAnswer: "Listen, reflect, and respond constructively",
                    skill: "feedback_reception"
                },
                {
                    id: 3,
                    question: "When managing a project with a tight deadline, what should be prioritized?",
                    options: ["Adding extra features", "Working longer hours", "Clear communication and scope management", "Cutting quality assurance"],
                    correctAnswer: "Clear communication and scope management",
                    skill: "project_management"
                },
                {
                    id: 4,
                    question: "What is the best approach when you don't know the answer to a question in your area of expertise?",
                    options: ["Make an educated guess", "Admit you don't know but will find out", "Redirect to another topic", "Provide a vague response"],
                    correctAnswer: "Admit you don't know but will find out",
                    skill: "honesty"
                },
                {
                    id: 5,
                    question: "Which communication style is most effective in a professional setting?",
                    options: ["Direct and concise", "Detailed and comprehensive", "Casual and friendly", "It depends on the context and audience"],
                    correctAnswer: "It depends on the context and audience",
                    skill: "communication"
                }
            ];
        }
        
        questions = mockQuestions;
        currentQuestionIndex = 0;
        userAnswers = [];
        startTime = new Date();
        startQuiz();
    }
    
    function startQuiz() {
        localStorage.setItem("isAttemptingQuiz", true);
        categoryView.style.display = 'none';
        quizView.style.display = 'block';
        displayQuestion();
    }
    
    function displayQuestion() {
        const question = questions[currentQuestionIndex];
        questionText.textContent = question.question;
        
        const progress = ((currentQuestionIndex + 1) / questions.length) * 100;
        quizProgress.style.width = `${progress}%`;
        questionCounter.textContent = `Question ${currentQuestionIndex + 1} of ${questions.length}`;
        
        optionsContainer.innerHTML = '';
        
        question.options.forEach((option, index) => {
            const button = document.createElement('button');
            button.className = 'btn btn-outline-primary mb-2 text-start';
            button.textContent = option;
            button.addEventListener('click', () => handleAnswer(option));
            optionsContainer.appendChild(button);
        });
    }
    
    function handleAnswer(selectedOption) {
        const question = questions[currentQuestionIndex];
        
        userAnswers.push({
            questionId: question.id,
            question: question.question,
            selectedOption: selectedOption,
            correctAnswer: question.correctAnswer,
            isCorrect: selectedOption === question.correctAnswer,
            skill: question.skill
        });
        
        currentQuestionIndex++;
        
        if (currentQuestionIndex < questions.length) {
            displayQuestion();
        } else {
            finishQuiz();
        }
    }
    
    function finishQuiz() {
        const endTime = new Date();
        const timeTaken = Math.round((endTime - startTime) / 1000); // in seconds
        
        quizView.style.display = 'none';
        resultsView.style.display = 'block';
        
        const correctAnswers = userAnswers.filter(answer => answer.isCorrect).length;
        const score = Math.round((correctAnswers / questions.length) * 100);
        
        const resultsContainer = document.getElementById('results-container');
        resultsContainer.innerHTML = `
            <div class="mb-3">
                <h5>Score: ${score}%</h5>
                <p>Correct answers: ${correctAnswers} out of ${questions.length}</p>
                <p>Time taken: ${formatTime(timeTaken)}</p>
            </div>
        `;
        
        const skillMapping = mapSkills(userAnswers, currentCategory);
        
        const proficientSkillsList = document.getElementById('proficient-skills');
        proficientSkillsList.innerHTML = '';
        
        skillMapping.proficient.forEach(skill => {
            const li = document.createElement('li');
            li.textContent = formatSkillName(skill);
            proficientSkillsList.appendChild(li);
        });
        
        const improvementSkillsList = document.getElementById('improvement-skills');
        improvementSkillsList.innerHTML = '';
        
        skillMapping.needsImprovement.forEach(skill => {
            const li = document.createElement('li');
            li.textContent = formatSkillName(skill);
            improvementSkillsList.appendChild(li);
        });
        
        localStorage.setItem('userSkills', JSON.stringify({
            category: currentCategory,
            proficientSkills: skillMapping.proficient,
            improvementSkills: skillMapping.needsImprovement,
            score: score,
            completedAt: new Date().toISOString()
        }));
    }
    
    function mapSkills(answers, category) {
        const skillResults = {};
        
        answers.forEach(answer => {
            if (!skillResults[answer.skill]) {
                skillResults[answer.skill] = {
                    total: 0,
                    correct: 0
                };
            }
            
            skillResults[answer.skill].total++;
            if (answer.isCorrect) {
                skillResults[answer.skill].correct++;
            }
        });
        
        const proficient = [];
        const needsImprovement = [];
        
        for (const skill in skillResults) {
            const result = skillResults[skill];
            const proficiency = (result.correct / result.total) * 100;
            
            if (proficiency >= 70) {
                proficient.push(skill);
            } else {
                needsImprovement.push(skill);
            }
        }
        
        return {
            proficient: proficient,
            needsImprovement: needsImprovement
        };
    }



function submitQuizResults(results) {
    const userId = getUserIdFromSession();
    console.log("Submitting quiz results with user ID:", userId);
    
    if (userId) {
        results.user_id = userId;
        
        fetch('/api/submit_quiz_results', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(results)
        })
        .then(response => response.json())
        .then(data => {
            console.log('Success:', data);
            
            if (data.success) {
                updateUserSkills(results);
            }
            
            if (userId) {
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 2000);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    } else {
        console.log("No user ID available, results stored locally only");
    }
}

// function submitQuizResults(results) {
//     // Add user ID if available from session
//     const userIdElement = document.getElementById('user-id');
//     console.log(userIdElement)
//     if (userIdElement && userIdElement.value) {
//         results.user_id = parseInt(userIdElement.value);
        
//         // Submit to server
//         fetch('/api/submit_quiz_results', {
//             method: 'POST',
//             headers: {
//                 'Content-Type': 'application/json',
//             },
//             body: JSON.stringify(results)
//         })
//         .then(response => response.json())
//         .then(data => {
//             console.log('Success:', data);
            
//             // Optional: Update the user's skills in their profile
//             if (data.success) {
//                 updateUserSkills(results);
//             }
//         })
//         .catch(error => {
//             console.error('Error:', error);
//         });
//     } else {
//         // Store locally only if not logged in
//         localStorage.setItem('userSkills', JSON.stringify(results));
//     }
// }

function updateUserSkills(skillData) {
    fetch('/api/update_user_skills', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(skillData)
    })
    .then(response => response.json())
    .then(data => {
        console.log('Skills updated:', data);
    })
    .catch(error => {
        console.error('Error updating skills:', error);
    });
}

function getUserIdFromSession() {
    const userIdElement = document.getElementById('user-id');
    if (userIdElement && userIdElement.value) {
        const userId = parseInt(userIdElement.value, 10);
        console.log("Found user ID:", userId);
        if (!isNaN(userId)) {
            return userId;
        }
    }
    console.log("No valid user ID found in session");
    return null;
}


function finishQuiz() {
    const endTime = new Date();
    const timeTaken = Math.round((endTime - startTime) / 1000); // in seconds
    
    quizView.style.display = 'none';
    resultsView.style.display = 'block';
    
    const correctAnswers = userAnswers.filter(answer => answer.isCorrect).length;
    const score = Math.round((correctAnswers / questions.length) * 100);
    
    const resultsContainer = document.getElementById('results-container');
    resultsContainer.innerHTML = `
        <div class="mb-3">
            <h5>Score: ${score}%</h5>
            <p>Correct answers: ${correctAnswers} out of ${questions.length}</p>
            <p>Time taken: ${formatTime(timeTaken)}</p>
        </div>
    `;
    
    const skillMapping = mapSkills(userAnswers, currentCategory);
    
    const proficientSkillsList = document.getElementById('proficient-skills');
    proficientSkillsList.innerHTML = '';
    
    skillMapping.proficient.forEach(skill => {
        const li = document.createElement('li');
        li.textContent = formatSkillName(skill);
        proficientSkillsList.appendChild(li);
    });
    
    const improvementSkillsList = document.getElementById('improvement-skills');
    improvementSkillsList.innerHTML = '';
    
    skillMapping.needsImprovement.forEach(skill => {
        const li = document.createElement('li');
        li.textContent = formatSkillName(skill);
        improvementSkillsList.appendChild(li);
    });
    
    const quizResults = {
        category: currentCategory,
        proficientSkills: skillMapping.proficient,
        improvementSkills: skillMapping.needsImprovement,
        score: score,
        completedAt: new Date().toISOString()
    };
    
    localStorage.setItem('userSkills', JSON.stringify(quizResults));
    
    submitQuizResults(quizResults);
}
    
    function formatSkillName(skill) {
        const skillNames = {
            // Technical skills
            'front_end': 'Front-End Development',
            'back_end': 'Back-End Development',
            'database': 'Database Management',
            'data_structures': 'Data Structures & Algorithms',
            
            // Soft skills
            'conflict_resolution': 'Conflict Resolution',
            'feedback_reception': 'Receiving Feedback',
            'project_management': 'Project Management',
            'honesty': 'Honesty & Transparency',
            'communication': 'Communication Skills'
        };
        
        return skillNames[skill] || skill.replace('_', ' ');
    }
    
    function formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}m ${remainingSeconds}s`;
    }
});