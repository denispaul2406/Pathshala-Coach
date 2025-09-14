import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Progress } from './components/ui/progress';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Alert, AlertDescription } from './components/ui/alert';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { RadioGroup, RadioGroupItem } from './components/ui/radio-group';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { CheckCircle, Clock, BookOpen, TrendingUp, Target, Globe, Phone, User, Brain, Trophy, Calendar, ArrowRight, Star, Zap, Timer, BarChart3 } from 'lucide-react';
import { useToast } from './hooks/use-toast';
import { Toaster } from './components/ui/sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [currentScreen, setCurrentScreen] = useState('onboarding'); // onboarding, dashboard, diagnostic, practice, results
  const [user, setUser] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [assessmentId, setAssessmentId] = useState(null);
  const [language, setLanguage] = useState('english');
  const [timeLeft, setTimeLeft] = useState(300); // 5 minutes per question
  const [progress, setProgress] = useState(null);
  const [userProgress, setUserProgress] = useState(null);
  const [dailyGoal, setDailyGoal] = useState(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showStudyPlan, setShowStudyPlan] = useState(false);
  const { toast } = useToast();

  // Load user from localStorage on app start
  useEffect(() => {
    const savedUser = localStorage.getItem('pathshala_user');
    if (savedUser) {
      try {
        const userData = JSON.parse(savedUser);
        setUser(userData);
        setLanguage(userData.preferred_language || 'english');
        setCurrentScreen('dashboard');
        fetchUserProgress(userData.id);
      } catch (error) {
        console.error('Error loading saved user:', error);
        localStorage.removeItem('pathshala_user');
      }
    }
  }, []);

  // Timer effect
  useEffect(() => {
    if (currentScreen === 'diagnostic' && timeLeft > 0) {
      const timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [timeLeft, currentScreen]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleUserRegistration = async (formData) => {
    setIsLoading(true);
    try {
      const response = await axios.post(`${API}/users`, {
        name: formData.name,
        phone: formData.phone,
        target_exam: formData.target_exam,
        preferred_language: formData.preferred_language || 'english'
      });
      setUser(response.data);
      setLanguage(response.data.preferred_language);
      
      // Save user to localStorage for session persistence
      localStorage.setItem('pathshala_user', JSON.stringify(response.data));
      
      await fetchUserProgress(response.data.id);
      setCurrentScreen('dashboard');
      toast({
        title: "Welcome to Pathshala Coach! 🎯",
        description: "Your AI-powered learning journey begins now!"
      });
    } catch (error) {
      console.error('Registration error:', error);
      toast({
        title: "Registration failed",
        description: "Please try again",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const fetchUserProgress = async (userId) => {
    try {
      const [progressResponse, studyPlanResponse, assessmentsResponse] = await Promise.all([
        axios.get(`${API}/progress/${userId}`),
        axios.get(`${API}/study-plan/${userId}`),
        axios.get(`${API}/assessments/${userId}`)
      ]);
      
      // Calculate actual progress from assessments
      const assessments = assessmentsResponse.data.assessments;
      const completedTests = assessments.filter(a => a.completed_at);
      const totalQuestionsAnswered = completedTests.reduce((sum, test) => sum + (test.answers ? test.answers.length : 0), 0);
      
      // Also count questions from incomplete tests
      const incompleteTests = assessments.filter(a => !a.completed_at);
      const incompleteQuestions = incompleteTests.reduce((sum, test) => sum + (test.answers ? test.answers.length : 0), 0);
      
      const totalQuestions = totalQuestionsAnswered + incompleteQuestions;
      
      setUserProgress({
        ...progressResponse.data,
        total_tests_taken: completedTests.length,
        questions_completed: totalQuestions,
        total_assessments: assessments.length
      });
      setDailyGoal(studyPlanResponse.data);
      
      // Debug logging
      console.log('Study Plan Data:', studyPlanResponse.data);
      console.log('Progress Data:', progressResponse.data);
    } catch (error) {
      console.error('Failed to fetch user progress:', error);
    }
  };

  const startDiagnosticTest = async () => {
    setIsLoading(true);
    try {
      const response = await axios.post(`${API}/diagnostic-test?user_id=${user.id}`);
      setQuestions(response.data.questions);
      setAssessmentId(response.data.assessment_id);
      setCurrentQuestion(0);
      setAnswers([]);
      setCurrentScreen('diagnostic');
      setTimeLeft(300);
      toast({
        title: "Diagnostic Test Started! 🧠",
        description: "10 questions to assess your current level"
      });
    } catch (error) {
      console.error('Failed to start test:', error);
      toast({
        title: "Failed to start test",
        description: "Please try again",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const submitAnswer = async (answerIndex) => {
    if (selectedAnswer === null) return;
    
    setIsLoading(true);
    try {
      const response = await axios.post(`${API}/submit-answer`, {
        assessment_id: assessmentId,
        question_id: questions[currentQuestion].id,
        selected_option: selectedAnswer,
        time_taken: 300 - timeLeft
      });
      
      setAnswers([...answers, {
        question_id: questions[currentQuestion].id,
        selected_option: selectedAnswer,
        is_correct: response.data.is_correct,
        explanation: response.data.explanation
      }]);

      setFeedback(response.data);
      setShowExplanation(true);
      
    } catch (error) {
      console.error('Failed to submit answer:', error);
      toast({
        title: "Failed to submit answer",
        description: "Please try again",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const nextQuestion = () => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
      setSelectedAnswer(null);
      setTimeLeft(300);
      setShowExplanation(false);
      setFeedback(null);
    } else {
      completeAssessment();
    }
  };

  const completeAssessment = async () => {
    setIsLoading(true);
    try {
      const response = await axios.post(`${API}/complete-assessment?assessment_id=${assessmentId}`);
      setProgress(response.data);
      await fetchUserProgress(user.id); // Refresh user progress
      setCurrentScreen('results');
      toast({
        title: "Assessment Complete! 🎉",
        description: `You scored ${response.data.overall_score.toFixed(1)}%`
      });
    } catch (error) {
      console.error('Failed to complete assessment:', error);
      toast({
        title: "Failed to complete assessment",
        description: "Please try again",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getAdaptivePractice = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(`${API}/adaptive-practice?user_id=${user.id}&count=5`);
      setQuestions(response.data.questions);
      setAssessmentId(response.data.assessment_id);
      setCurrentQuestion(0);
      setAnswers([]);
      setCurrentScreen('practice');
      setTimeLeft(300);
      toast({
        title: "Adaptive Practice Started! ⚡",
        description: "Questions tailored to your skill level"
      });
    } catch (error) {
      console.error('Failed to get practice questions:', error);
      // Show user-friendly error message
      if (error.response?.status === 429) {
        toast({
          title: "API Limit Reached",
          description: "Using sample questions for demo. Upgrade for unlimited AI questions!",
          variant: "default"
        });
      } else {
        toast({
          title: "Demo Mode",
          description: "Showing sample questions (API limit reached)",
          variant: "default"
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const viewStudyPlan = () => {
    if (dailyGoal) {
      setShowStudyPlan(true);
      setCurrentScreen('study-plan');
    } else {
      toast({
        title: "Study Plan Loading...",
        description: "Please wait while we generate your personalized plan",
        variant: "default"
      });
    }
  };

  const OnboardingScreen = () => {
    const [formData, setFormData] = useState({
      name: '',
      phone: '',
      target_exam: '',
      preferred_language: 'english'
    });

    const handleSubmit = (e) => {
      e.preventDefault();
      if (!formData.name || !formData.phone || !formData.target_exam) {
        toast({
          title: "Please fill all fields",
          variant: "destructive"
        });
        return;
      }
      handleUserRegistration(formData);
    };

    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-2xl border-0 bg-white/90 backdrop-blur-sm">
          <CardHeader className="text-center space-y-4">
            <div className="mx-auto w-16 h-16 gradient-openai rounded-full flex items-center justify-center">
              <Brain className="w-8 h-8 text-white" />
            </div>
            <CardTitle className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              Pathshala Coach
            </CardTitle>
            <CardDescription className="text-slate-600">
              AI-Powered Adaptive Microlearning
              <br />
              <span className="text-sm text-blue-600 font-medium">
                {language === 'hindi' ? 'प्रतियोगी परीक्षा की तैयारी' : 'Built for OpenAI x NxtWave Buildathon'}
              </span>
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name" className="flex items-center gap-2">
                  <User className="w-4 h-4" />
                  {language === 'hindi' ? 'नाम' : 'Full Name'}
                </Label>
                <Input
                  id="name"
                  type="text"
                  placeholder={language === 'hindi' ? 'अपना नाम डालें' : 'Enter your name'}
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  className="border-slate-200 focus:border-emerald-400"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="phone" className="flex items-center gap-2">
                  <Phone className="w-4 h-4" />
                  {language === 'hindi' ? 'फोन नंबर' : 'Phone Number'}
                </Label>
                <Input
                  id="phone"
                  type="tel"
                  placeholder={language === 'hindi' ? '+91 XXXXX XXXXX' : '+91 XXXXX XXXXX'}
                  value={formData.phone}
                  onChange={(e) => setFormData({...formData, phone: e.target.value})}
                  className="border-slate-200 focus:border-emerald-400"
                />
              </div>

              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Target className="w-4 h-4" />
                  {language === 'hindi' ? 'लक्षित परीक्षा' : 'Target Exam'}
                </Label>
                <Select value={formData.target_exam} onValueChange={(value) => setFormData({...formData, target_exam: value})}>
                  <SelectTrigger className="border-slate-200 focus:border-emerald-400">
                    <SelectValue placeholder={language === 'hindi' ? 'परीक्षा चुनें' : 'Select your exam'} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="SSC">SSC (CGL, CHSL, MTS)</SelectItem>
                    <SelectItem value="Banking">Banking (SBI, IBPS)</SelectItem>
                    <SelectItem value="State PSC">State PSC</SelectItem>
                    <SelectItem value="Railway">Railway Exams</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Globe className="w-4 h-4" />
                  {language === 'hindi' ? 'भाषा' : 'Preferred Language'}
                </Label>
                <Select 
                  value={formData.preferred_language} 
                  onValueChange={(value) => {
                    setFormData({...formData, preferred_language: value});
                    setLanguage(value);
                  }}
                >
                  <SelectTrigger className="border-slate-200 focus:border-emerald-400">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="english">English</SelectItem>
                    <SelectItem value="hindi">हिंदी</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button 
                type="submit" 
                className="w-full gradient-openai hover:opacity-90 text-white font-medium py-2.5"
                disabled={isLoading}
              >
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    {language === 'hindi' ? 'प्रतीक्षा करें...' : 'Getting Started...'}
                  </div>
                ) : (
                  <>
                    {language === 'hindi' ? 'शुरू करें' : 'Start Learning'}
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  };

  const DashboardScreen = () => {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
        <div className="container mx-auto px-4 py-6">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-slate-800">
              {language === 'hindi' ? 'नमस्ते' : 'Welcome'}, {user?.name}! 👋
            </h1>
            <p className="text-slate-600 mt-1">
              {language === 'hindi' ? 'आज क्या सीखना है?' : 'Ready to ace your'} {user?.target_exam} {language === 'hindi' ? 'परीक्षा' : 'exam'}?
            </p>
          </div>

          {/* Quick Actions */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <Card className="gradient-openai text-white border-0 hover:shadow-lg transition-all duration-300 hover:scale-105">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-lg mb-2">
                      {language === 'hindi' ? 'निदान परीक्षा' : 'Diagnostic Test'}
                    </h3>
                    <p className="text-white/80 text-sm mb-4">
                      {language === 'hindi' ? '10 प्रश्न • 15 मिनट' : '10 Questions • 15 Minutes'}
                    </p>
                    <Button 
                      variant="secondary" 
                      size="sm"
                      onClick={startDiagnosticTest}
                      disabled={isLoading}
                      className="bg-white text-green-600 hover:bg-gray-50"
                    >
                      {language === 'hindi' ? 'शुरू करें' : 'Start Now'}
                      <Brain className="w-4 h-4 ml-2" />
                    </Button>
                  </div>
                  <Target className="w-12 h-12 text-white/80" />
                </div>
              </CardContent>
            </Card>

            <Card className="gradient-buildathon text-white border-0 hover:shadow-lg transition-all duration-300 hover:scale-105">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-lg mb-2">
                      {language === 'hindi' ? 'अनुकूली अभ्यास' : 'Adaptive Practice'}
                    </h3>
                    <p className="text-white/80 text-sm mb-4">
                      {language === 'hindi' ? 'AI द्वारा तैयार' : 'AI-Powered Questions'}
                    </p>
                    <Button 
                      variant="secondary" 
                      size="sm"
                      onClick={getAdaptivePractice}
                      disabled={isLoading}
                      className="bg-white text-blue-600 hover:bg-gray-50"
                    >
                      {language === 'hindi' ? 'अभ्यास करें' : 'Practice'}
                      <Zap className="w-4 h-4 ml-2" />
                    </Button>
                  </div>
                  <BookOpen className="w-12 h-12 text-white/80" />
                </div>
              </CardContent>
            </Card>

            <Card className="gradient-innovation text-white border-0 hover:shadow-lg transition-all duration-300 hover:scale-105">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-lg mb-2">
                      {language === 'hindi' ? 'दैनिक योजना' : 'Daily Plan'}
                    </h3>
                    <p className="text-white/80 text-sm mb-4">
                      {language === 'hindi' ? '20 मिनट • स्मार्ट सिलेक्शन' : '20 Minutes • Smart Selection'}
                    </p>
                    <Button 
                      variant="secondary" 
                      size="sm"
                      className="bg-white text-purple-600 hover:bg-gray-50"
                      onClick={viewStudyPlan}
                    >
                      {language === 'hindi' ? 'देखें' : 'View Plan'}
                      <Calendar className="w-4 h-4 ml-2" />
                    </Button>
                  </div>
                  <Clock className="w-12 h-12 text-white/80" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Today's Goal */}
          <Card className="mb-6 bg-white shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-slate-800">
                <Trophy className="w-5 h-5 text-yellow-500" />
                {language === 'hindi' ? 'आज का लक्ष्य' : "Today's Goal"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-3">
                <span className="text-slate-600">
                  {language === 'hindi' ? 'दैनिक अभ्यास पूरा करें' : 'Complete Daily Practice'}
                </span>
                <Badge variant="outline" className="text-emerald-600 border-emerald-200">
                  {userProgress?.questions_completed || 0}/{dailyGoal?.questions_count || 20} {language === 'hindi' ? 'प्रश्न' : 'Questions'}
                </Badge>
              </div>
              <Progress value={Math.min(((userProgress?.questions_completed || 0) / (dailyGoal?.questions_count || 20)) * 100, 100)} className="h-2" />
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card className="bg-white shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-slate-800">
                <BarChart3 className="w-5 h-5 text-blue-500" />
                {language === 'hindi' ? 'हाल की गतिविधि' : 'Recent Activity'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {userProgress && userProgress.total_tests_taken > 0 ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center">
                        <Trophy className="w-4 h-4 text-white" />
                      </div>
                      <div>
                        <p className="font-medium text-emerald-800">
                          {language === 'hindi' ? 'परीक्षा पूर्ण' : 'Test Completed'}
                        </p>
                        <p className="text-sm text-emerald-600">
                          {language === 'hindi' ? 'औसत अंक:' : 'Average Score:'} {userProgress.average_score}%
                        </p>
                      </div>
                    </div>
                    <Badge variant="outline" className="text-emerald-600 border-emerald-200">
                      {userProgress.total_tests_taken} {language === 'hindi' ? 'परीक्षाएं' : 'tests'}
                    </Badge>
                  </div>
                  
                  {userProgress.improvement_trend !== 0 && (
                    <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                          <TrendingUp className="w-4 h-4 text-white" />
                        </div>
                        <div>
                          <p className="font-medium text-blue-800">
                            {language === 'hindi' ? 'प्रगति का रुझान' : 'Progress Trend'}
                          </p>
                          <p className="text-sm text-blue-600">
                            {userProgress.improvement_trend > 0 ? '⬆️' : '⬇️'} {Math.abs(userProgress.improvement_trend).toFixed(1)}% {language === 'hindi' ? 'परिवर्तन' : 'change'}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500">
                  <BookOpen className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                  <p>{language === 'hindi' ? 'अभी तक कोई गतिविधि नहीं' : 'No activity yet'}</p>
                  <p className="text-sm mt-1">
                    {language === 'hindi' ? 'डायग्नोस्टिक टेस्ट से शुरुआत करें' : 'Start with the diagnostic test'}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    );
  };

  const DiagnosticTestScreen = () => {
    const question = questions[currentQuestion];
    const questionText = language === 'hindi' ? question?.question_text_hi : question?.question_text_en;
    const options = language === 'hindi' ? question?.options_hi : question?.options_en;

    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
        <div className="container mx-auto px-4 py-6">
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-2xl font-bold text-slate-800">
                {language === 'hindi' ? 'निदान परीक्षा' : 'Diagnostic Test'}
              </h1>
              <p className="text-slate-600">
                {language === 'hindi' ? 'प्रश्न' : 'Question'} {currentQuestion + 1} of {questions.length}
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Badge variant="outline" className="text-blue-600 border-blue-200">
                <Timer className="w-4 h-4 mr-1" />
                {formatTime(timeLeft)}
              </Badge>
            </div>
          </div>

          {/* Progress */}
          <div className="mb-6">
            <div className="flex justify-between text-sm text-slate-600 mb-2">
              <span>{language === 'hindi' ? 'प्रगति' : 'Progress'}</span>
              <span>{Math.round(((currentQuestion + 1) / questions.length) * 100)}%</span>
            </div>
            <Progress value={((currentQuestion + 1) / questions.length) * 100} className="h-2" />
          </div>

          {/* Question Card */}
          <Card className="mb-6 bg-white shadow-lg">
            <CardHeader>
              <div className="flex items-center gap-2 mb-2">
                <Badge variant="secondary" className="capitalize">
                  {question?.subject?.replace('_', ' ')}
                </Badge>
                <Badge variant="outline">
                  {question?.difficulty}
                </Badge>
              </div>
              <CardTitle className="text-lg leading-relaxed">
                {questionText}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!showExplanation ? (
                <RadioGroup 
                  value={selectedAnswer?.toString()} 
                  onValueChange={(value) => setSelectedAnswer(parseInt(value))}
                  className="space-y-3"
                >
                  {options?.map((option, index) => (
                    <div key={index} className="flex items-center space-x-3 p-3 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors">
                      <RadioGroupItem value={index.toString()} id={`option-${index}`} />
                      <Label htmlFor={`option-${index}`} className="flex-1 cursor-pointer text-sm">
                        <span className="font-medium text-slate-700 mr-2">
                          {String.fromCharCode(65 + index)}.
                        </span>
                        {option}
                      </Label>
                    </div>
                  ))}
                </RadioGroup>
              ) : (
                <div className="space-y-4">
                  {/* Result */}
                  <Alert className={feedback?.is_correct ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}>
                    <CheckCircle className={`w-4 h-4 ${feedback?.is_correct ? 'text-green-600' : 'text-red-600'}`} />
                    <AlertDescription className={feedback?.is_correct ? 'text-green-800' : 'text-red-800'}>
                      {feedback?.is_correct 
                        ? (language === 'hindi' ? '✅ सही उत्तर!' : '✅ Correct!')
                        : (language === 'hindi' ? '❌ गलत उत्तर' : '❌ Incorrect')
                      }
                      {!feedback?.is_correct && (
                        <span className="block mt-1">
                          {language === 'hindi' ? 'सही उत्तर:' : 'Correct answer:'} {String.fromCharCode(65 + feedback?.correct_answer)} - {options?.[feedback?.correct_answer]}
                        </span>
                      )}
                    </AlertDescription>
                  </Alert>

                  {/* Explanation */}
                  <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                    <h4 className="font-medium text-blue-900 mb-2">
                      {language === 'hindi' ? '📚 व्याख्या' : '📚 Explanation'}
                    </h4>
                    <p className="text-blue-800 text-sm leading-relaxed">
                      {language === 'hindi' ? feedback?.explanation?.hindi : feedback?.explanation?.english}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <div className="flex justify-center">
            {!showExplanation ? (
              <Button 
                onClick={submitAnswer}
                disabled={selectedAnswer === null || isLoading}
                className="gradient-openai hover:opacity-90 text-white px-8 py-2"
                size="lg"
              >
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    {language === 'hindi' ? 'जमा किया जा रहा है...' : 'Submitting...'}
                  </div>
                ) : (
                  <>
                    {language === 'hindi' ? 'उत्तर जमा करें' : 'Submit Answer'}
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </>
                )}
              </Button>
            ) : (
              <Button 
                onClick={nextQuestion}
                className="gradient-buildathon hover:opacity-90 text-white px-8 py-2"
                size="lg"
              >
                {currentQuestion < questions.length - 1 
                  ? (language === 'hindi' ? 'अगला प्रश्न' : 'Next Question')
                  : (language === 'hindi' ? 'परीक्षा समाप्त करें' : 'Finish Test')
                }
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  };

  const ResultsScreen = () => {
    const getScoreColor = (score) => {
      if (score >= 80) return 'text-green-600';
      if (score >= 60) return 'text-yellow-600';
      return 'text-red-600';
    };

    const getScoreBadge = (score) => {
      if (score >= 80) return { variant: 'default', className: 'bg-green-100 text-green-800', text: language === 'hindi' ? 'उत्कृष्ट' : 'Excellent' };
      if (score >= 60) return { variant: 'secondary', className: 'bg-yellow-100 text-yellow-800', text: language === 'hindi' ? 'अच्छा' : 'Good' };
      return { variant: 'destructive', className: 'bg-red-100 text-red-800', text: language === 'hindi' ? 'सुधार की आवश्यकता' : 'Needs Improvement' };
    };

    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50">
        <div className="container mx-auto px-4 py-6">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-20 h-20 gradient-openai rounded-full flex items-center justify-center mx-auto mb-4">
              <Trophy className="w-10 h-10 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-slate-800 mb-2">
              {language === 'hindi' ? 'परीक्षा पूर्ण!' : 'Test Complete!'}
            </h1>
            <p className="text-slate-600">
              {language === 'hindi' ? 'आपका परिणाम तैयार है' : 'Your AI-powered assessment results are ready'}
            </p>
          </div>

          {/* Overall Score */}
          <Card className="mb-6 bg-white shadow-lg">
            <CardContent className="p-8 text-center">
              <div className="mb-4">
                <span className={`text-5xl font-bold ${getScoreColor(progress?.overall_score)}`}>
                  {progress?.overall_score?.toFixed(1)}%
                </span>
              </div>
              <Badge className={getScoreBadge(progress?.overall_score).className}>
                {getScoreBadge(progress?.overall_score).text}
              </Badge>
              <p className="text-slate-600 mt-2">
                {progress?.correct_answers} {language === 'hindi' ? 'सही' : 'correct'} out of {progress?.total_questions} {language === 'hindi' ? 'प्रश्न' : 'questions'}
              </p>
            </CardContent>
          </Card>

          {/* Subject-wise Breakdown */}
          <Card className="mb-6 bg-white shadow-lg">
            <CardHeader>
              <CardTitle className="text-center">
                {language === 'hindi' ? 'विषयवार प्रदर्शन' : 'Subject-wise Performance'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(progress?.subject_scores || {}).map(([subject, score]) => (
                  <div key={subject}>
                    <div className="flex justify-between items-center mb-2">
                      <span className="capitalize font-medium text-slate-700">
                        {subject.replace('_', ' ')}
                      </span>
                      <span className={`font-bold ${getScoreColor(score)}`}>
                        {score.toFixed(1)}%
                      </span>
                    </div>
                    <Progress value={score} className="h-2" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Recommendations */}
          <Card className="mb-6 bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
            <CardHeader>
              <CardTitle className="text-blue-800 flex items-center gap-2">
                <Star className="w-5 h-5" />
                {language === 'hindi' ? 'व्यक्तिगत सुझाव' : 'Personalized Recommendations'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-white p-4 rounded-lg border border-blue-200">
                  <h4 className="font-medium text-blue-900 mb-2 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    {language === 'hindi' ? 'मजबूत क्षेत्र' : 'Strong Areas'}
                  </h4>
                  <ul className="space-y-1">
                    {Object.entries(progress?.subject_scores || {})
                      .filter(([_, score]) => score >= 70)
                      .map(([subject, score]) => (
                        <li key={subject} className="text-sm text-green-700 capitalize">
                          ✅ {subject.replace('_', ' ')} ({score.toFixed(1)}%)
                        </li>
                      ))
                    }
                  </ul>
                </div>
                <div className="bg-white p-4 rounded-lg border border-blue-200">
                  <h4 className="font-medium text-blue-900 mb-2 flex items-center gap-2">
                    <Target className="w-4 h-4" />
                    {language === 'hindi' ? 'सुधार के क्षेत्र' : 'Focus Areas'}
                  </h4>
                  <ul className="space-y-1">
                    {Object.entries(progress?.subject_scores || {})
                      .filter(([_, score]) => score < 70)
                      .map(([subject, score]) => (
                        <li key={subject} className="text-sm text-orange-700 capitalize">
                          📈 {subject.replace('_', ' ')} ({score.toFixed(1)}%)
                        </li>
                      ))
                    }
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button 
              onClick={getAdaptivePractice}
              className="gradient-openai hover:opacity-90 text-white px-8 py-3"
              size="lg"
            >
              <Zap className="w-5 h-5 mr-2" />
              {language === 'hindi' ? 'अनुकूली अभ्यास शुरू करें' : 'Start AI-Powered Practice'}
            </Button>
            <Button 
              variant="outline" 
              onClick={() => setCurrentScreen('dashboard')}
              className="border-slate-300 hover:bg-slate-50 px-8 py-3"
              size="lg"
            >
              {language === 'hindi' ? 'डैशबोर्ड पर जाएं' : 'Back to Dashboard'}
            </Button>
          </div>
        </div>
      </div>
    );
  };

  const PracticeScreen = () => {
    // Similar to DiagnosticTestScreen but for adaptive practice
    return DiagnosticTestScreen(); // Reusing the same component for now
  };

  const StudyPlanScreen = () => {
    const getSubjectIcon = (subject) => {
      switch (subject) {
        case 'quantitative':
          return '🔢';
        case 'reasoning':
          return '🧩';
        case 'english':
          return '📚';
        case 'general_knowledge':
          return '🌍';
        default:
          return '📖';
      }
    };

    const getSubjectName = (subject) => {
      switch (subject) {
        case 'quantitative':
          return language === 'hindi' ? 'गणित' : 'Quantitative Aptitude';
        case 'reasoning':
          return language === 'hindi' ? 'तर्कशक्ति' : 'Logical Reasoning';
        case 'english':
          return language === 'hindi' ? 'अंग्रेजी' : 'English Language';
        case 'general_knowledge':
          return language === 'hindi' ? 'सामान्य ज्ञान' : 'General Knowledge';
        default:
          return subject;
      }
    };

    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
        <div className="container mx-auto px-4 py-6">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-20 h-20 gradient-innovation rounded-full flex items-center justify-center mx-auto mb-4">
              <Calendar className="w-10 h-10 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-slate-800 mb-2">
              {language === 'hindi' ? 'आपकी दैनिक अध्ययन योजना' : 'Your Daily Study Plan'}
            </h1>
            <p className="text-slate-600">
              {language === 'hindi' ? 'AI द्वारा तैयार व्यक्तिगत योजना' : 'AI-Powered Personalized Learning Plan'}
            </p>
          </div>

          {/* Study Plan Overview */}
          <Card className="mb-6 bg-white shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-slate-800">
                <Clock className="w-5 h-5 text-purple-500" />
                {language === 'hindi' ? 'आज का अध्ययन लक्ष्य' : "Today's Learning Goal"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-6">
                <div className="text-center p-4 bg-gradient-to-br from-purple-50 to-indigo-50 rounded-lg border border-purple-200">
                  <div className="text-2xl font-bold text-purple-600 mb-1">
                    {dailyGoal?.questions_count || 20}
                  </div>
                  <div className="text-sm text-purple-700">
                    {language === 'hindi' ? 'प्रश्न' : 'Questions'}
                  </div>
                </div>
                <div className="text-center p-4 bg-gradient-to-br from-blue-50 to-cyan-50 rounded-lg border border-blue-200">
                  <div className="text-2xl font-bold text-blue-600 mb-1">
                    {dailyGoal?.estimated_time || 20}
                  </div>
                  <div className="text-sm text-blue-700">
                    {language === 'hindi' ? 'मिनट' : 'Minutes'}
                  </div>
                </div>
                <div className="text-center p-4 bg-gradient-to-br from-emerald-50 to-green-50 rounded-lg border border-emerald-200">
                  <div className="text-2xl font-bold text-emerald-600 mb-1">
                    {dailyGoal?.subjects?.length || 2}
                  </div>
                  <div className="text-sm text-emerald-700">
                    {language === 'hindi' ? 'विषय' : 'Subjects'}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Focus Subjects */}
          <Card className="mb-6 bg-white shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-slate-800">
                <Target className="w-5 h-5 text-orange-500" />
                {language === 'hindi' ? 'आज के लिए फोकस विषय' : 'Focus Subjects for Today'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-4">
                {dailyGoal?.subjects?.map((subject, index) => (
                  <div key={index} className="flex items-center gap-4 p-4 bg-gradient-to-r from-orange-50 to-yellow-50 rounded-lg border border-orange-200">
                    <div className="text-3xl">
                      {getSubjectIcon(subject)}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-orange-800">
                        {getSubjectName(subject)}
                      </h3>
                      <p className="text-sm text-orange-600">
                        {language === 'hindi' ? 'अभ्यास के लिए अनुशंसित' : 'Recommended for practice'}
                      </p>
                    </div>
                    <Badge variant="outline" className="text-orange-600 border-orange-300">
                      {language === 'hindi' ? 'फोकस' : 'Focus'}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Study Schedule */}
          <Card className="mb-6 bg-white shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-slate-800">
                <Clock className="w-5 h-5 text-blue-500" />
                {language === 'hindi' ? 'अध्ययन समय सारिणी' : 'Study Schedule'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-lg border border-blue-200">
                  <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center">
                    <span className="text-white font-bold">1</span>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-blue-800">
                      {language === 'hindi' ? 'वार्म-अप (5 मिनट)' : 'Warm-up (5 minutes)'}
                    </h3>
                    <p className="text-sm text-blue-600">
                      {language === 'hindi' ? 'आसान प्रश्नों से शुरुआत करें' : 'Start with easy questions to build confidence'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border border-purple-200">
                  <div className="w-12 h-12 bg-purple-500 rounded-full flex items-center justify-center">
                    <span className="text-white font-bold">2</span>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-purple-800">
                      {language === 'hindi' ? 'मुख्य अभ्यास (10 मिनट)' : 'Main Practice (10 minutes)'}
                    </h3>
                    <p className="text-sm text-purple-600">
                      {language === 'hindi' ? 'फोकस विषयों पर गहन अभ्यास' : 'Intensive practice on focus subjects'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-emerald-50 to-green-50 rounded-lg border border-emerald-200">
                  <div className="w-12 h-12 bg-emerald-500 rounded-full flex items-center justify-center">
                    <span className="text-white font-bold">3</span>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-emerald-800">
                      {language === 'hindi' ? 'समीक्षा (5 मिनट)' : 'Review (5 minutes)'}
                    </h3>
                    <p className="text-sm text-emerald-600">
                      {language === 'hindi' ? 'गलत उत्तरों की समीक्षा और सीखना' : 'Review mistakes and learn from them'}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Progress Tracking */}
          <Card className="mb-6 bg-white shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-slate-800">
                <TrendingUp className="w-5 h-5 text-green-500" />
                {language === 'hindi' ? 'प्रगति ट्रैकिंग' : 'Progress Tracking'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border border-green-200">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                      <CheckCircle className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <p className="font-medium text-green-800">
                        {language === 'hindi' ? 'पूर्ण किए गए प्रश्न' : 'Questions Completed'}
                      </p>
                      <p className="text-sm text-green-600">
                        {userProgress?.questions_completed || 0} / {dailyGoal?.questions_count || 20}
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-green-600 border-green-300">
                    {Math.round(((userProgress?.questions_completed || 0) / (dailyGoal?.questions_count || 20)) * 100)}%
                  </Badge>
                </div>

                <div className="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-lg border border-blue-200">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                      <Trophy className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <p className="font-medium text-blue-800">
                        {language === 'hindi' ? 'औसत स्कोर' : 'Average Score'}
                      </p>
                      <p className="text-sm text-blue-600">
                        {userProgress?.average_score || 0}% {language === 'hindi' ? 'सटीकता' : 'accuracy'}
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-blue-600 border-blue-300">
                    {userProgress?.total_tests_taken || 0} {language === 'hindi' ? 'परीक्षाएं' : 'tests'}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button 
              onClick={getAdaptivePractice}
              className="gradient-openai hover:opacity-90 text-white px-8 py-3"
              size="lg"
            >
              <Zap className="w-5 h-5 mr-2" />
              {language === 'hindi' ? 'अभ्यास शुरू करें' : 'Start Practice'}
            </Button>
            <Button 
              variant="outline" 
              onClick={() => setCurrentScreen('dashboard')}
              className="border-slate-300 hover:bg-slate-50 px-8 py-3"
              size="lg"
            >
              {language === 'hindi' ? 'डैशबोर्ड पर जाएं' : 'Back to Dashboard'}
            </Button>
          </div>
        </div>
      </div>
    );
  };

  // Render appropriate screen
  const renderCurrentScreen = () => {
    switch (currentScreen) {
      case 'onboarding':
        return <OnboardingScreen />;
      case 'dashboard':
        return <DashboardScreen />;
      case 'diagnostic':
        return <DiagnosticTestScreen />;
      case 'practice':
        return <PracticeScreen />;
      case 'results':
        return <ResultsScreen />;
      case 'study-plan':
        return <StudyPlanScreen />;
      default:
        return <OnboardingScreen />;
    }
  };

  return (
    <div className="App">
      {/* OpenAI Buildathon Header */}
      {currentScreen !== 'onboarding' && (
        <div className="bg-white border-b border-slate-200 px-4 py-3">
          <div className="container mx-auto flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 gradient-openai rounded-full flex items-center justify-center">
                <Brain className="w-4 h-4 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-slate-800">Pathshala Coach</h1>
                <p className="text-xs text-slate-500">Built for OpenAI x NxtWave Buildathon</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setLanguage(language === 'english' ? 'hindi' : 'english')}
                className="border-slate-200 text-slate-600 hover:bg-slate-50"
              >
                <Globe className="w-4 h-4 mr-1" />
                {language === 'english' ? 'हिंदी' : 'English'}
              </Button>
            </div>
          </div>
        </div>
      )}
      {renderCurrentScreen()}
      <Toaster />
    </div>
  );
}

export default App;