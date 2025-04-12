// virtual_interview.js

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const startInterviewBtn = document.getElementById('start-interview');
    const submitAnswerBtn = document.getElementById('submit-answer');
    const newInterviewBtn = document.getElementById('new-interview');
    const saveResultsBtn = document.getElementById('save-results');
    const startRecordingBtn = document.getElementById('start-recording');
    const stopRecordingBtn = document.getElementById('stop-recording');
    
    // Interview state
    let interviewId = null;
    let currentQuestion = '';
    let questionNumber = 1;
    let useVoiceRecognition = false;
    let recognition = null;
    
    // Initialize speech recognition if available
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.continuous = true;
        recognition.interimResults = true;
        
        recognition.onresult = function(event) {
            let interimTranscript = '';
            let finalTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }
            
            // Update the answer text area
            const answerText = document.getElementById('answer-text');
            answerText.value = finalTranscript || interimTranscript;
            
            // Update recording status
            const recordingStatus = document.getElementById('recording-status');
            recordingStatus.textContent = interimTranscript ? 'Listening: ' + interimTranscript : 'Listening...';
        };
        
        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            stopRecording();
        };
    }
    
    // Event listeners
    if (startInterviewBtn) {
        startInterviewBtn.addEventListener('click', startInterview);
    }
    
    if (submitAnswerBtn) {
        submitAnswerBtn.addEventListener('click', submitAnswer);
    }
    
    if (newInterviewBtn) {
        newInterviewBtn.addEventListener('click', resetInterview);
    }
    
    if (saveResultsBtn) {
        saveResultsBtn.addEventListener('click', saveResults);
    }
    
    if (startRecordingBtn) {
        startRecordingBtn.addEventListener('click', startRecording);
    }
    
    if (stopRecordingBtn) {
        stopRecordingBtn.addEventListener('click', stopRecording);
    }
    
    // Initialize interview
    function startInterview() {
        console.log('Starting interview...');
        const jobRoleSelect = document.getElementById('job-role');
        const skillAreaSelect = document.getElementById('skill-area');
        const useVoiceCheckbox = document.getElementById('use-voice');
        
        const jobRoleId = jobRoleSelect.value;
        const jobRoleText = jobRoleSelect.options[jobRoleSelect.selectedIndex].text;
        const skillArea = skillAreaSelect.value;
        useVoiceRecognition = useVoiceCheckbox.checked;
        
        // Show loading state
        startInterviewBtn.disabled = true;
        startInterviewBtn.innerHTML = 'Starting interview...';
        
        // Call the API to start the interview
        fetch('/api/start_interview', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                job_role: jobRoleText,
                skill_area: skillArea
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Interview started:', data);
            interviewId = data.interview_id;
            
            // Show the interview in progress UI
            document.getElementById('interview-setup').style.display = 'none';
            document.getElementById('interview-in-progress').style.display = 'block';
            
            // Update the UI with the greeting and first question
            document.getElementById('greeting').textContent = data.greeting;
            document.getElementById('current-question').textContent = data.first_question;
            currentQuestion = data.first_question;
            
            // Set interviewer name
            document.getElementById('interviewer-name').textContent = `${jobRoleText} Interviewer`;
            
            // Enable speech if selected
            if (useVoiceRecognition && recognition) {
                document.getElementById('speech-controls').style.display = 'block';
            } else {
                document.getElementById('speech-controls').style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error starting interview:', error);
            alert('There was an error starting the interview. Please try again.');
            startInterviewBtn.disabled = false;
            startInterviewBtn.innerHTML = 'Start Interview';
        });
    }
    
    // Submit answer and get next question
    function submitAnswer() {
        const answerText = document.getElementById('answer-text').value.trim();
        
        if (!answerText) {
            alert('Please provide an answer before continuing.');
            return;
        }
        
        // Stop recording if active
        if (recognition && recognition.recognizing) {
            stopRecording();
        }
        
        // Disable submit button
        submitAnswerBtn.disabled = true;
        submitAnswerBtn.innerHTML = 'Processing...';
        
        // Add the current Q&A to the history
        addQuestionAnswerToHistory(currentQuestion, answerText);
        
        // Submit the answer to get the next question
        fetch('/api/submit_interview_answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                interview_id: interviewId,
                question: currentQuestion,
                answer: answerText
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Next question data:', data);
            
            // Check if this was the final question
            if (data.is_final) {
                // Show a "Complete Interview" button instead of submit
                document.getElementById('current-question').textContent = data.next_question;
                currentQuestion = data.next_question;
                
                // Clear answer box
                document.getElementById('answer-text').value = '';
                
                // Change button to "Complete Interview"
                submitAnswerBtn.innerHTML = 'Complete Interview';
                submitAnswerBtn.classList.remove('btn-primary');
                submitAnswerBtn.classList.add('btn-success');
                submitAnswerBtn.disabled = false;
                
                // Change onclick behavior for the button
                submitAnswerBtn.removeEventListener('click', submitAnswer);
                submitAnswerBtn.addEventListener('click', completeInterview);
            } else {
                // Update the UI with the next question
                document.getElementById('current-question').textContent = data.next_question;
                currentQuestion = data.next_question;
                
                // Clear answer box and re-enable submit
                document.getElementById('answer-text').value = '';
                submitAnswerBtn.disabled = false;
                submitAnswerBtn.innerHTML = 'Submit Answer';
                
                questionNumber++;
            }
        })
        .catch(error => {
            console.error('Error submitting answer:', error);
            alert('There was an error processing your answer. Please try again.');
            submitAnswerBtn.disabled = false;
            submitAnswerBtn.innerHTML = 'Submit Answer';
        });
    }
    
    // Add a Q&A pair to the conversation history
    function addQuestionAnswerToHistory(question, answer) {
        const qaContainer = document.getElementById('qa-container');
        
        // Create Q&A elements
        const qaDiv = document.createElement('div');
        qaDiv.className = 'mb-3';
        
        const questionDiv = document.createElement('div');
        questionDiv.className = 'alert alert-secondary';
        questionDiv.textContent = `Q${questionNumber}: ${question}`;
        
        const answerDiv = document.createElement('div');
        answerDiv.className = 'alert alert-light';
        answerDiv.textContent = `A: ${answer}`;
        
        // Add to container
        qaDiv.appendChild(questionDiv);
        qaDiv.appendChild(answerDiv);
        qaContainer.appendChild(qaDiv);
    }
    
    // Complete the interview and show results
    function completeInterview() {
        // First submit the last answer
        const answerText = document.getElementById('answer-text').value.trim();
        
        if (!answerText) {
            alert('Please provide an answer before completing the interview.');
            return;
        }
        
        // Show loading state
        submitAnswerBtn.disabled = true;
        submitAnswerBtn.innerHTML = 'Analyzing interview...';
        
        // Add the final Q&A to the history
        addQuestionAnswerToHistory(currentQuestion, answerText);
        
        // Submit the final answer
        fetch('/api/submit_interview_answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                interview_id: interviewId,
                question: currentQuestion,
                answer: answerText,
                is_final: true
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(() => {
            // Now complete the interview and get results
            return fetch('/api/complete_interview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    interview_id: interviewId
                })
            });
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Interview completed:', data);
            
            // Switch to results view
            document.getElementById('interview-in-progress').style.display = 'none';
            document.getElementById('interview-results').style.display = 'block';
            
            // Update results UI
            updateResultsUI(data.analysis, data.feedback);
        })
        .catch(error => {
            console.error('Error completing interview:', error);
            alert('There was an error analyzing your interview. Please try again.');
            submitAnswerBtn.disabled = false;
            submitAnswerBtn.innerHTML = 'Complete Interview';
        });
    }
    
    // Update the results UI with analysis and feedback
    function updateResultsUI(analysis, feedback) {
        // Update scores
        const technicalScore = document.getElementById('technical-score');
        const communicationScore = document.getElementById('communication-score');
        
        technicalScore.style.width = `${analysis.technical_score}%`;
        technicalScore.textContent = `${analysis.technical_score}%`;
        technicalScore.setAttribute('aria-valuenow', analysis.technical_score);
        
        communicationScore.style.width = `${analysis.communication_score}%`;
        communicationScore.textContent = `${analysis.communication_score}%`;
        communicationScore.setAttribute('aria-valuenow', analysis.communication_score);
        
        // Update lists
        const strengthsList = document.getElementById('strengths-list');
        const improvementsList = document.getElementById('improvements-list');
        const nextStepsList = document.getElementById('next-steps-list');
        
        // Clear previous items
        strengthsList.innerHTML = '';
        improvementsList.innerHTML = '';
        nextStepsList.innerHTML = '';
        
        // Add strengths
        if (analysis.strengths && analysis.strengths.length) {
            analysis.strengths.forEach(strength => {
                const li = document.createElement('li');
                li.className = 'list-group-item';
                li.textContent = strength;
                strengthsList.appendChild(li);
            });
        }
        
        // Add areas for improvement
        if (feedback.areas_for_improvement && feedback.areas_for_improvement.length) {
            feedback.areas_for_improvement.forEach(improvement => {
                const li = document.createElement('li');
                li.className = 'list-group-item';
                li.textContent = improvement;
                improvementsList.appendChild(li);
            });
        }
        
        // Add next steps
        if (feedback.next_steps && feedback.next_steps.length) {
            feedback.next_steps.forEach(step => {
                const li = document.createElement('li');
                li.className = 'list-group-item';
                li.textContent = step;
                nextStepsList.appendChild(li);
            });
        }
        
        // Update overall feedback
        document.getElementById('overall-feedback').textContent = feedback.overall_feedback || 'Thank you for completing the practice interview.';
    }
    
    // Reset for a new interview
    function resetInterview() {
        // Reset interview state
        interviewId = null;
        currentQuestion = '';
        questionNumber = 1;
        
        // Reset UI components
        document.getElementById('interview-setup').style.display = 'block';
        document.getElementById('interview-in-progress').style.display = 'none';
        document.getElementById('interview-results').style.display = 'none';
        
        document.getElementById('greeting').textContent = '';
        document.getElementById('current-question').textContent = '';
        document.getElementById('answer-text').value = '';
        document.getElementById('qa-container').innerHTML = '';
        
        // Reset buttons
        startInterviewBtn.disabled = false;
        startInterviewBtn.innerHTML = 'Start Interview';
        submitAnswerBtn.disabled = false;
        submitAnswerBtn.innerHTML = 'Submit Answer';
        submitAnswerBtn.classList.add('btn-primary');
        submitAnswerBtn.classList.remove('btn-success');
        
        // Reset event listeners
        submitAnswerBtn.removeEventListener('click', completeInterview);
        submitAnswerBtn.addEventListener('click', submitAnswer);
        
        // Stop any active recording
        if (recognition && recognition.recognizing) {
            stopRecording();
        }
    }
    
    // Save interview results to profile
    function saveResults() {
        if (!interviewId) {
            alert('No interview data to save.');
            return;
        }
        
        saveResultsBtn.disabled = true;
        saveResultsBtn.innerHTML = 'Saving...';
        
        fetch('/api/save_interview_results', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                interview_id: interviewId
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert('Interview results saved to your profile!');
                // Redirect to dashboard
                window.location.href = '/dashboard';
            } else {
                throw new Error(data.error || 'Failed to save results');
            }
        })
        .catch(error => {
            console.error('Error saving results:', error);
            alert('There was an error saving your results. Please try again.');
            saveResultsBtn.disabled = false;
            saveResultsBtn.innerHTML = 'Save Results to Profile';
        });
    }
    
    // Voice recognition functions
    function startRecording() {
        if (!recognition) {
            alert('Speech recognition is not supported in your browser.');
            return;
        }
        
        try {
            recognition.start();
            recognition.recognizing = true;
            
            // Update UI
            startRecordingBtn.style.display = 'none';
            stopRecordingBtn.style.display = 'inline-block';
            document.getElementById('recording-status').style.display = 'block';
            document.getElementById('recording-status').textContent = 'Listening...';
        } catch (error) {
            console.error('Error starting speech recognition:', error);
        }
    }
    
    function stopRecording() {
        if (!recognition) return;
        
        try {
            recognition.stop();
            recognition.recognizing = false;
            
            // Update UI
            startRecordingBtn.style.display = 'inline-block';
            stopRecordingBtn.style.display = 'none';
            document.getElementById('recording-status').style.display = 'none';
        } catch (error) {
            console.error('Error stopping speech recognition:', error);
        }
    }
});