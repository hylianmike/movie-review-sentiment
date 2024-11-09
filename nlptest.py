import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from pandas import *
import spacy
from pandas import *
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import hstack

# nltk.download('vader_lexicon')

nlp = spacy.load("en_core_web_sm")

stop_words = set(stopwords.words('english'))  # Create a set of English stopwords for filtering

vader = SentimentIntensityAnalyzer()

data = read_csv('prepro-data.csv', encoding='latin-1')

labels = data.iloc[:, 0]
reviews = data.iloc[:, 1]
exclaims = data.iloc[:, 2]

def stem(text):
    if text.endswith("ss") or (text.endswith("ly") and text != "only") or text.endswith("ed"):
        text = text[:-2]
    elif text.endswith('ies'):
        text = text[:-3] + "y"
    elif text.endswith('s'):
        text = text[:-1]
    elif text.endswith('ing'):
        text = text[:-3]
    elif text.endswith('ness'):
        text = text[:-4]
    return text

positive_words = [
    "excellent", "amazing", "fantastic", "wonderful", "superb", "great", 
    "impressive", "delightful", "positive", "brilliant", "perfect", 
    "awesome", "outstanding", "enjoyable", "love", "recommend", 
    "satisfied", "best", "flawless", "beautiful", "worth", 
    "remarkable", "exciting", "refreshing", "exceptional", 
    "pleasant", "liked", "helpful", "terrific", "good", "stunning"
]

negative_words = [
    "terrible", "awful", "disappointing", "poor", "hate", "absurd",
    "horrible", "unsatisfactory", "worst", "annoying", "waste", 
    "flawed", "problem", "regret", "boring", "dreadful", 
    "frustrating", "unacceptable", "mediocre", "negative", 
    "dislike", "unimpressive", "confusing", "dull", "lacking",
    "unfortunate", "disappointed", "rough"
]

adverbs = [
    "absolute", "amazing", "awful", "bare", "complete", "deep", "enormous",
    "entire", "especial", "extreme", "fabulous", "fair", "frightful", 
    "ful", "great", "hard", "high", "huge", "incredib", "insane", 
    "intense", "literal", "mild", "moderate", "particular", "phenomenal", 
    "pure", "quite", "rather", "real", "remarkab", "serious", "significant",
    "slight", "so", "somewhat", "strong", "surprising", "terrib", "thorough", 
    "total", "tremendous", "tru", "utter", "very", "virtual", "wild"
]

doc = nlp(" ".join(positive_words))
lemmatized_positive = [token.lemma_.lower() for token in doc]
doc = nlp(" ".join(negative_words))
lemmatized_negative = [token.lemma_.lower() for token in doc]

def getOnlyCount(tokens):
    return len(list((i for i, n in enumerate(tokens) if n == 'only')))

def getPositiveCount(tokens):
    sum = 0
    for i in range(0, len(tokens)):
        if tokens[i] in lemmatized_positive:
            sum += 1
            if i != 0 and tokens[i - 1] in adverbs:
                sum += 1
    return sum

def getNegativeCount(tokens):
    sum = 0
    for i in range(0, len(tokens)):
        if tokens[i] in lemmatized_negative:
            sum += 1
            if i != 0 and tokens[i - 1] in adverbs:
                sum += 1
    return sum

def getReverseSentiment(tokens):
    lines = []
    negatives = []
    result = 0
    only = list((i for i, n in enumerate(tokens) if n == 'only'))
    for o in only:
        try:
            lines.append([tokens[o + 1], tokens[o + 2], tokens[o + 3], tokens[o - 1]])
            negatives.append([tokens[o - 1]])
        except IndexError:
            continue
    for words in lines:
        for w in words:
            if w in lemmatized_positive:
                if words[-1] == 'not':
                    result += 1
                else: 
                    result -= 1
            elif w in lemmatized_negative:
                if words[-1] == 'not':
                    result -= 1
                else: 
                    result += 1
    return result

def getVaderScore(text):
    compound = vader.polarity_scores(text)['compound']
    if compound >= 0:
        return 0
    else:
        return 1

features = []

i = 0
for r in reviews:
    tokens = word_tokenize(r)
    stemmed = [stem(word.lower()) for word in tokens]
    features.append([getPositiveCount(stemmed), getNegativeCount(stemmed), getReverseSentiment(stemmed), getVaderScore(r) * (exclaims[i] + 1)])
    i += 1

tfidf_vectorizer = TfidfVectorizer()
tfidf_matrix = tfidf_vectorizer.fit_transform(reviews)
combined_features = hstack([features, tfidf_matrix])

x_train, x_test, y_train, y_test = train_test_split(combined_features, labels, test_size=0.3, random_state=42)

classifiers = {
    "K-Nearest Neighbours": KNeighborsClassifier(n_neighbors=3),
    "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
    "Decision Tree": DecisionTreeClassifier(),
    "Support Vector Machine": LinearSVC(dual=True)
}

# fitting, predicting, and printing the accuracy for all the classifiers listed above
for name, classifier in classifiers.items():
    classifier.fit(x_train, y_train)
    y_pred = classifier.predict(x_test)
    accuracy = accuracy_score(y_test, y_pred)
    print("Accuracy on " + name + ":", accuracy)