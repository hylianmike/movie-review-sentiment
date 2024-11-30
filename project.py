import warnings
import nltk
import numpy as np
import seaborn as sns
import spacy
import os
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from nltk import pos_tag
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from pandas import *
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.metrics import confusion_matrix
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import hstack
from mlxtend.feature_selection import SequentialFeatureSelector as sfs
from csv import writer
from collections import Counter

# ignore warnings, mainly generated by the Linear SVC class
warnings.filterwarnings('ignore')

# downloading nltk packages for VADER and part-of-speech tagging
nltk.download('vader_lexicon')
nltk.download('averaged_perceptron_tagger_eng')

# load the small model from spaCy for NLP tasks
nlp = spacy.load("en_core_web_sm")

# create a list of English stopwords for filtering in getMostCommonWords and getMostCommonPhrases functions
stop_words = set(stopwords.words('english'))

# initialize a vader object
vader = SentimentIntensityAnalyzer()



#########################
# 1. DATA PREPROCESSING #
#########################

print()

# dictionary maps sentiment labels to the corresponding directories containing the source data from Kaggle
allFiles = {
    0: 'train/neg', # 0 -> negative sentiment reviews (in the 'train/neg' directory)
    1: 'train/pos', # 1 -> positive sentiment reviews (in the 'train/pos' directory)
}

# define the name of the csv file containing data before preprocessing
originalFile = "data2.csv"

# if not already done, convert data from multiple source files (from Kaggle) to a single csv with columns:
#   1. Value (0 for negative sentiment, 1 for positive sentiment)
#   2. Review (text content of the movie review)
#   3. Score (star rating of movie from 1-10)
if not os.path.exists(originalFile):
    print("--> Converting source data to csv...", end='')
    with open(originalFile, 'a') as file:
        w = writer(file)
        w.writerow(["value","review","score"])
        for value, path in allFiles.items():
            for f in os.listdir(path):
                words = open(path + "/" + f, encoding="utf-8")
                review = words.read()
                try:
                    w.writerow([value, review, (f.split('.')[0]).split('_')[-1]])
                except UnicodeEncodeError:
                    continue
    print("Complete.")
else:
    print(f"--> Source data already converted to csv in {originalFile}")


# define the name of the file containing the preprocessed data
preprocessed_file = 'processed-data.csv'

# if the preprocessed data file exists, then load it
if os.path.exists(preprocessed_file):
    print(f"--> Loading preprocessed data from {preprocessed_file}...", end='')
    preprocessed_df = pd.read_csv(preprocessed_file)
    print("Complete.")

# otherwise, preprocess the data
else:
    # define the name of the file containing the preprocessed data
    data = pd.read_csv(originalFile, encoding='latin-1')

    # console progress bar variables (preprocessing can be lengthy)
    total_reviews_to_process = len(data.index)
    iteration = 1
    previous_print = -5

    preprocessed_reviews = []
    exclaims = []

    print("--> Preprocessing data:", end=' ')

    for review in data['review']:

        # progress bar
        percent_complete = (iteration / total_reviews_to_process) * 100
        if (int(percent_complete) == previous_print+5):
            print(f"{int(percent_complete)}%", end='...')
            previous_print = int(percent_complete)
            

        # remove br tags
        review_without_br = review.replace('<br />', '')

        doc = nlp(review_without_br)

        # tokenize reviews, convert token to lowercase, lemmatize tokens, remove stop words, and remove punctuation
        filtered_tokens = [
            token.lemma_.lower()
            for token in doc
                if not token.is_stop and
                    not token.is_punct
        ]

        # append preprocessed review as a single string to list
        preprocessed_reviews.append(' '.join(filtered_tokens))

        # append amount of exclamation marks in the review 
        exclaims.append(review_without_br.count('!'))

        # used in progress bar
        iteration += 1

    print("Complete.")

    # save preprocessed reviews to a CSV file
    print(f"--> Saving preprocessed data to {preprocessed_file}...", end='')
    preprocessed_df = pd.DataFrame({
        'value': data['value'],
        'review': preprocessed_reviews,
        'score': data['score'],
        'exclaim': exclaims
    })
    preprocessed_df.to_csv(preprocessed_file, index=False)
    print("Complete.")



#################################################################
# 2. FEATURE EXTRACTION USING MANUAL FEATURES AND TF-IDF SCORES #
#################################################################

# read the newly formatted .csv file
data = read_csv('processed-data.csv', encoding='latin-1')

print("hello")

# get the values from the .csv
labels = data.iloc[:, 0]
reviews = data.iloc[:, 1]
exclaims = data.iloc[:, 3]

# method to stem a given word
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

# list of a bunch of examples of positive words
positive_words = [
    "excellent", "amazing", "fantastic", "wonderful", "superb", "great", 
    "impressive", "delightful", "positive", "brilliant", "perfect", 
    "awesome", "outstanding", "enjoyable", "love", "recommend", 
    "satisfied", "best", "flawless", "beautiful", "worth", 
    "remarkable", "exciting", "refreshing", "exceptional", 
    "pleasant", "liked", "helpful", "terrific", "good", "stunning"
]

# list of a bunch of examples of negative words
negative_words = [
    "terrible", "awful", "disappointing", "poor", "hate", "absurd",
    "horrible", "unsatisfactory", "worst", "annoying", "waste", 
    "flawed", "problem", "regret", "boring", "dreadful", 
    "frustrating", "unacceptable", "mediocre", "negative", 
    "dislike", "unimpressive", "confusing", "dull", "lacking",
    "unfortunate", "disappointed", "rough"
]

# list of a bunch of adverbs
adverb_words = [
    "absolute", "amazing", "awful", "bare", "complete", "deep", "enormous",
    "entire", "especial", "extreme", "fabulous", "fair", "frightful", 
    "ful", "great", "hard", "high", "huge", "incredib", "insane", 
    "intense", "literal", "mild", "moderate", "particular", "phenomenal", 
    "pure", "quite", "rather", "real", "remarkab", "serious", "significant",
    "slight", "so", "somewhat", "strong", "surprising", "terrib", "thorough", 
    "total", "tremendous", "tru", "utter", "very", "virtual", "wild"
]

# lemmatizing all the positive and negative words above
doc = nlp(" ".join(positive_words))
lemmatized_positive = [token.lemma_.lower() for token in doc]
doc = nlp(" ".join(negative_words))
lemmatized_negative = [token.lemma_.lower() for token in doc]

# return the amount of times the word "only" occurs in a string (not actually used)
def getOnlyCount(tokens):
    return len(list((i for i, n in enumerate(tokens) if n == 'only')))

# return the amount of positive words found in a string
# if an adverb is the previous word, then increase the score
def getPositiveCount(tokens):
    sum = 0
    for i in range(0, len(tokens)):
        if tokens[i] in lemmatized_positive:
            sum += 1
            if i != 0 and tokens[i - 1] in adverb_words:
                sum += 1
    return sum

# return the amount of negative words found in a string
# if an adverb is the negative word, then increase the score
# also, if an "**" is found (representing vocal profanity), the score is increased
def getNegativeCount(tokens):
    sum = 0
    for i in range(0, len(tokens)):
        if tokens[i] in lemmatized_negative or "**" in tokens[i]:
            sum += 1
            if i != 0 and tokens[i - 1] in adverb_words:
                sum += 1
    return sum

# return a number showcasing any "reverse sentiment" in a given string
# checking for any time an "only" appeared in the review, and increment / decrement a score based on if any of the following words are positive or negative
def getReverseSentiment(tokens):
    lines = []
    result = 0
    only = list((i for i, n in enumerate(tokens) if n == 'only'))
    for o in only:
        try:
            lines.append([tokens[o + 1], tokens[o + 2], tokens[o + 3], tokens[o - 1]])
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

# method to return the compound VADER score of a given string (is not actually used)
def getVaderScore(text):
    compound = vader.polarity_scores(text)['compound']
    if compound >= 0:
        return 0
    else:
        return 1

# method to return the adjective to adverb ratio
def getAdvToAdjRatio(text):
    tags = pos_tag(text)
    adjectives = 0
    adv = 0
    for word, tag in tags:
        if tag.startswith("JJ"):
            adjectives += 1
        elif tag.startswith("RB"):
            adv += 1
    return adv / adjectives if adjectives > 0 else 0

# function to return the average VADER score of all the words in a string
def getAverageVaderScore(words):
    total = 0
    i = 0
    for word in words:
        total += vader.polarity_scores(word)['compound']
        i += 1
    return total / i if i > 0 else 0

# generating features
features = []
i = 0

# loop through all the reviews
for r in reviews:
    # create arrays for all types of words to examine
    nouns = []
    adjectives = []
    verbs = []
    adverbs = []
    # generate tokens and tags for each word
    tokens = word_tokenize(r)
    tags = pos_tag(tokens)
    # append each word to one of the arrays based on what POS tag is
    for word, tag in tags:
        if tag.startswith("NN"):
            nouns.append(word)
        elif tag.startswith("JJ"):
            adjectives.append(word)
        elif tag.startswith("V"):
            verbs.append(word)
        elif tag.startswith("RB"):
            adverbs.append(word)
    # stem each word in the review
    stemmed = [stem(word.lower()) for word in tokens]
    # append all features of the review to the master array
    features.append([getPositiveCount(stemmed), getNegativeCount(stemmed), getReverseSentiment(stemmed), getAdvToAdjRatio(stemmed),
                     getAverageVaderScore(nouns), getAverageVaderScore(adjectives), getAverageVaderScore(verbs), getAverageVaderScore(adverbs),
                     len(stemmed), exclaims[i]])
    i += 1

# retrieving the TF-IDF scores of the reviews to be used by the classifiers later
tfidf_vectorizer = TfidfVectorizer()
tfidf_matrix = tfidf_vectorizer.fit_transform(reviews)



#####################################
# 3. TRAINING AND EVALUATING MODELS #
#####################################

# creating classifiers
classifiers = {
    "K-Nearest Neighbours": KNeighborsClassifier(n_neighbors=3),
    "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
    "Decision Tree": DecisionTreeClassifier(),
    "Support Vector Machine": LinearSVC(dual=True)
}

# creating collections to check against later for visualizations
scores = {}
selectedScores = {}
x_tests = {}

# fitting, predicting, and printing the accuracy for all the classifiers listed above
for name, classifier in classifiers.items():

    # combining the manual features with the TF-IDF scores
    combined_features = hstack([features, tfidf_matrix])

    # training and testing the model with the combined features, and checking for accuracy
    x_train, x_test, y_train, y_test = train_test_split(combined_features, labels, test_size=0.3, random_state=42)
    classifier.fit(x_train, y_train)
    y_pred = classifier.predict(x_test)
    accuracy = accuracy_score(y_test, y_pred)
    print("Accuracy on " + name + ":", accuracy)
    scores[name] = accuracy

    # turn features into a numpy array
    if isinstance(features, list):
        features = np.array(features)

    # creating the feature selection object
    feature_selector = sfs(classifier, k_features=4, forward=False, verbose=0, scoring='accuracy')
    # doing analysis to find the four best features for the particular classifier
    feature_selector = feature_selector.fit(features, labels)
    # retrieving the names of the selected features
    feat_names = list(feature_selector.k_feature_names_)

    # taking the selected features and filtering the others out of the original features list
    selected_indices = [int(i) for i in feat_names]
    selected_features = features[:, selected_indices]
    combined_features = hstack([selected_features, tfidf_matrix])

    # training and testing the model with the newly combined features after feature selection, and checking for accuracy
    x_train, x_test, y_train, y_test = train_test_split(combined_features, labels, test_size=0.3, random_state=42)
    x_tests[name] = x_test
    classifier.fit(x_train, y_train)
    y_pred = classifier.predict(x_test)
    accuracy = accuracy_score(y_test, y_pred)
    print("Accuracy on " + name + ":", accuracy)
    selectedScores[name] = accuracy



#####################
# 4. VISUALIZATIONS #
#####################

preprocessed_lengths = preprocessed_df['review'].str.len()
posNegPalette = {'Positive': 'green', 'Negative': 'red'}
positiveReviews = preprocessed_df[preprocessed_df['value'] == 1]
negativeReviews = preprocessed_df[preprocessed_df['value'] == 0]



##### DISTRIBUTION OF SCORES #####
sns.histplot(preprocessed_df['score'], bins=10, kde=True, color='purple')
plt.title('Distribution of Review Scores')
plt.xlabel('Score')
plt.ylabel('Frequency')
plt.show()

##### EXCLAMATION MARK GRAPH ######

# create labels for graph
bins = [0,1,2,3,4,5,6,7,8,9,10, float('inf')]
labels = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10+']

# separate reviews
negativeReviews.loc[:, 'exclaimBins'] = pd.cut(negativeReviews['exclaim'], bins=bins, labels=labels, right=False)
positiveReviews.loc[:, 'exclaimBins'] = pd.cut(positiveReviews['exclaim'], bins=bins, labels=labels, right=False)

negativeReviews.loc[:, 'reviewType'] = 'Negative'
positiveReviews.loc[:, 'reviewType'] = 'Positive'
combinedReviews = pd.concat([negativeReviews[['exclaimBins', 'reviewType']], positiveReviews[['exclaimBins', 'reviewType']]])

# count reviews in each bin for neg and pos reviews
reviewCounts = combinedReviews.groupby(['exclaimBins', 'reviewType']).size().reset_index(name='count')

# create graph
plt.figure(figsize=(10, 6))
sns.barplot(x='exclaimBins', y='count', hue='reviewType', data=reviewCounts, palette=posNegPalette)
plt.title('Distribution of Exclamation Marks in Positive and Negative Reviews')
plt.xlabel('Number of Exclamation Marks')
plt.ylabel('Frequency')
plt.legend(title='Review Type')
plt.show()



# for scores 1-10
sns.scatterplot(x=preprocessed_df['score'], y=preprocessed_df['exclaim'], alpha=0.5)
plt.title('Score vs. Number of Exclamation Marks')
plt.xlabel('Score')
plt.ylabel('Number of Exclamation Marks')
plt.xticks([1, 2, 3, 4, 7, 8, 9, 10])
plt.xlim(1, 10)
plt.show()

##### CHARACTER LENGTH GRAPH #####

positiveReviews = preprocessed_df[preprocessed_df['value'] == 1]['review']
negativeReviews = preprocessed_df[preprocessed_df['value'] == 0]['review']

positiveLengths = positiveReviews.str.len()
negativeLengths = negativeReviews.str.len()

# create graph
plt.figure(figsize=(10, 6))
sns.kdeplot(positiveLengths, label='Positive Reviews', color='green', shade=True)
sns.kdeplot(negativeLengths, label='Negative Reviews', color='red', shade=True)
plt.title('Review Length Distribution in Positive and Negative Reviews')
plt.xlabel('Review Length')
plt.ylabel('Density')
plt.legend()
plt.xlim(0, 3000)
plt.show()

avg_length_by_score = preprocessed_df.groupby('score')['review'].apply(lambda x: x.str.len().mean())
avg_length_by_score.plot(kind='bar', color='blue', alpha=0.7)
plt.title('Average Review Length by Score')
plt.xlabel('Score')
plt.ylabel('Average Length')
plt.show()

##### TOP TERMS USED IN REVIEWS #####

## using tfidf
featureNames = tfidf_vectorizer.get_feature_names_out()
termCount = tfidf_matrix.mean(axis=0).A1

sortedIndices = termCount.argsort()[::-1][:25]

# get top terms and the scores
topTerms = [featureNames[i] for i in sortedIndices]
topScores = [termCount[i] for i in sortedIndices]

# create graph
plt.figure(figsize=(10, 6))
sns.barplot(x=topScores, y=topTerms, palette="viridis")
plt.title('Top 25 Terms')
plt.xlabel('Score')
plt.ylabel('Terms')
plt.show()

##### MODEL ACCURACY COMPARISON #####

plt.figure(figsize=(10, 6))
sns.barplot(x=list(scores.values()), y=list(scores.keys()), palette='coolwarm')
plt.title('Model Accuracy Comparison (Before Backwards Selection)')
plt.xlabel('Accuracy')
plt.ylabel('Models')
plt.xlim(0.7, 1.0)
plt.show()

plt.figure(figsize=(10, 6))
sns.barplot(x=list(selectedScores.values()), y=list(selectedScores.keys()), palette='coolwarm')
plt.title('Model Accuracy Comparison (After Backwards Selection)')
plt.xlabel('Accuracy')
plt.ylabel('Models')
plt.xlim(0.7, 1.0)
plt.show()

##### CONFUSION MATRIX OF EACH MODEL #####

# the following will provide true pos, true neg, false pos, false neg of each model
for name, model in classifiers.items():
    y_pred = model.predict(x_tests[name])
    cm = confusion_matrix(y_test, y_pred)

    plt.figure(figsize=(6, 4))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=model.classes_, yticklabels=model.classes_)
    plt.title(f'Confusion Matrix for {name}')
    plt.xlabel('Predicted Labels')
    plt.ylabel('True Labels')
    plt.show()
    
    
##### MOST COMMON WORDS #####

def getMostCommonWords(reviews, top_n=20):
    excludeWords = {'movie', 'film', 'watch', 'know', 'thing', 'way', 'come'}
    vectorizer = CountVectorizer(stop_words='english', ngram_range=(1, 1))
    word_matrix = vectorizer.fit_transform(reviews)
    
    # sum up all word amounts
    wordFreq = word_matrix.sum(axis=0).A1
    words = vectorizer.get_feature_names_out()
    wordCount = dict(zip(words, wordFreq))
    filteredWordCount = {word: count for word, count in wordCount.items() if word not in excludeWords}
    commonWords = Counter(filteredWordCount).most_common(top_n)
    
    return commonWords

positiveCommonWords = getMostCommonWords(positiveReviews)
negativeCommonWords = getMostCommonWords(negativeReviews)
positiveWords, positiveCount = zip(*positiveCommonWords)
negativeWords, negativeCount = zip(*negativeCommonWords)

# plot results

plt.figure(figsize=(16, 10))

# positive
plt.subplot(1, 2, 1)
sns.barplot(x=list(positiveCount), y=list(positiveWords), palette="Greens_d")
plt.title('Top 20 Most Common Words in Positive Reviews')
plt.xlabel('Word Count')
plt.ylabel('Words')

# negative
plt.subplot(1, 2, 2)
sns.barplot(x=list(negativeCount), y=list(negativeWords), palette="Reds_d")
plt.title('Top 20 Most Common Words in Negative Reviews')
plt.xlabel('Word Count')
plt.ylabel('Words')

plt.tight_layout()
plt.show()

common_words_by_score = {}

# Process each score group
for group in preprocessed_df['score'].unique():
    groupReviews = preprocessed_df[preprocessed_df['score'] == group]['review']
    
    if groupReviews.empty:
        print(f"No reviews found for score {group}. Skipping.")
        continue  # Skip groups with no reviews

    # Get most common words for this score group
    common_words = getMostCommonWords(groupReviews, top_n=20)
    common_words_by_score[group] = common_words

# Prepare data for plotting
plot_data = []
for score, words in common_words_by_score.items():
    for word, count in words:
        plot_data.append({'Score': score, 'Word': word, 'Count': count})

plot_df = pd.DataFrame(plot_data)

# Plot the most common words by score
plt.figure(figsize=(12, 8))
sns.barplot(data=plot_df, x='Score', y='Count', hue='Word', palette='tab10')
plt.title('Most Common Words by Score')
plt.xlabel('Score')
plt.ylabel('Word Frequency')
plt.legend(title='Words', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.show()

##### MOST COMMON PHRASES #####

def getMostCommonPhrases(reviews, top_n=20):
    # use CountVectorizer to count phrases
    vectorizer = CountVectorizer(ngram_range=(2, 2), stop_words='english')
    phraseMatrix = vectorizer.fit_transform(reviews)
    phrases = vectorizer.get_feature_names_out()
    
    phraseCount = phraseMatrix.sum(axis=0).A1
    topPhrases = sorted(zip(phraseCount, phrases), reverse=True)[:top_n]
    
    return topPhrases 


positiveTopPhrases = getMostCommonPhrases(positiveReviews)
negativeTopPhrases = getMostCommonPhrases(negativeReviews)

# Prepare data for plotting
positivePhrases, positiveCount = zip(*positiveTopPhrases)
negativePhrases, negativeCount = zip(*negativeTopPhrases)

# plot results

plt.figure(figsize=(16, 10))

# positive
plt.subplot(1, 2, 1)
sns.barplot(x=list(positivePhrases), y=list(positiveCount), palette="Greens_d")
plt.title('Top 20 Phrases in Positive Reviews')
plt.xlabel('Phrase')
plt.ylabel('Frequency')

# negative
plt.subplot(1, 2, 2)
sns.barplot(x=list(negativePhrases), y=list(negativeCount), palette="Reds_d")
plt.title('Top 20 Phrases in Negative Reviews')
plt.xlabel('Phrase')
plt.ylabel('Frequency')

plt.tight_layout()
plt.show()

###### REVIEW LENGTH VS SCORE SANKEY #####
avg_length_by_score = preprocessed_df.groupby('score')['review'].apply(lambda x: x.str.len().mean())

# nodes
score_labels = [str(score) for score in avg_length_by_score.index]
lengths = avg_length_by_score.values
nodes = list(set(score_labels) | set([f'{score} - Length' for score in score_labels]))

# links
links = []
for score, length in zip(score_labels, lengths):
    links.append({
        'source': score_labels.index(str(score)),
        'target': len(score_labels) + score_labels.index(str(score)),
        'value': length
    })

# diagram
fig = go.Figure(go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=nodes,
        color="blue"
    ),
    link=dict(
        source=[link['source'] for link in links],
        target=[link['target'] for link in links],
        value=[link['value'] for link in links],
        color='rgba(0, 0, 255, 0.5)'
    )
))

fig.update_layout(title_text="Review Length vs Score", font_size=10)
fig.show()

##### ! VS SCORE SANKEY #####

bins = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, float('inf')]
labels = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10+']
preprocessed_df['exclaimBins'] = pd.cut(preprocessed_df['exclaim'], bins=bins, labels=labels, right=False)

# calculate frequency of exclamation bins by score
exclaim_bin_counts = preprocessed_df.groupby(['score', 'exclaimBins']).size().reset_index(name='count')

# nodes
score_labels = [str(score) for score in preprocessed_df['score'].unique()]
exclaim_labels = labels
nodes = score_labels + exclaim_labels

# links
links = []
for _, row in exclaim_bin_counts.iterrows():
    score_idx = score_labels.index(str(row['score']))
    exclaim_idx = len(score_labels) + exclaim_labels.index(row['exclaimBins'])
    links.append({
        'source': score_idx,
        'target': exclaim_idx,
        'value': row['count']
    })

# diagram
fig = go.Figure(go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=nodes,
        color="purple"
    ),
    link=dict(
        source=[link['source'] for link in links],
        target=[link['target'] for link in links],
        value=[link['value'] for link in links],
        color='rgba(255, 0, 0, 0.5)' 
    )
))

fig.update_layout(title_text="Exclamation Marks vs Score", font_size=10)
fig.show()