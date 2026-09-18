"""
populate_real_questions.py
---------------------------
Replaces the placeholder question_text/options/correct_option in
questions.csv with REAL, accurate multiple-choice questions.

IMPORTANT: This does NOT change question_id, topic, difficulty, or
prerequisite_topics for any row. attempts.csv references question_id and
denormalizes topic/difficulty from the ORIGINAL questions.csv -- since those
columns are untouched, attempts.csv remains fully valid after this script
runs. Only the human-facing content (what a student sees on quiz.html) is
being upgraded from placeholder text to real content.

HOW MATCHING WORKS:
    For each topic, the existing 12 rows already have a fixed distribution
    of difficulties (e.g. AI_Basics = three difficulty-1s, four
    difficulty-3s, four difficulty-4s, one difficulty-5 -- no difficulty-2).
    The REAL_QUESTIONS bank below is written with the EXACT same
    per-topic-per-difficulty counts, so each existing row is assigned a
    real question of the SAME difficulty it already had.
"""

import pandas as pd

QUESTIONS_CSV = "questions.csv"

# ---------------------------------------------------------------------------
# REAL QUESTION BANK
# Each topic: list of (difficulty, question_text, option_a, option_b,
#                       option_c, option_d, correct_option)
# ---------------------------------------------------------------------------
REAL_QUESTIONS = {

"Math_Basics": [
    (1, "What is 7 + 5 x 2?", "24", "17", "19", "14", "b"),
    (1, "Simplify: 3/6", "1/3", "2/3", "1/2", "3/4", "c"),
    (2, "Solve for x: 2x + 3 = 11", "3", "4", "5", "7", "b"),
    (2, "What is the value of 3^2 + 4^2?", "25", "7", "14", "49", "a"),
    (2, "What is the perimeter of a rectangle with length 8 and width 5?", "13", "26", "40", "18", "b"),
    (3, "Solve for x: x^2 - 5x + 6 = 0 (give the smaller root)", "2", "3", "-2", "6", "a"),
    (4, "What is the sum of the first 10 natural numbers?", "45", "50", "55", "60", "c"),
    (4, "Simplify: (2x^2)(3x^3)", "6x^5", "5x^6", "6x^6", "5x^5", "a"),
    (5, "What is the derivative of x^3 with respect to x?", "3x", "x^2", "3x^2", "x^3/3", "c"),
    (5, "Solve: log base 2 of 8 = ?", "2", "3", "4", "8", "b"),
    (5, "What is the sum of an infinite geometric series with first term 1 and ratio 1/2?", "1", "1.5", "2", "Infinite", "c"),
    (5, "If sin(theta) = 0.5, what is theta in degrees (0 to 90)?", "30", "45", "60", "90", "a"),
],

"Python": [
    (1, "Which symbol is used to start a single-line comment in Python?", "//", "#", "<!-- -->", "/* */", "b"),
    (1, "What is the correct file extension for Python files?", ".pt", ".pyt", ".py", ".python", "c"),
    (2, "What is the data type of the result of 3/2 in Python 3?", "int", "float", "str", "complex", "b"),
    (2, "Which keyword is used to define a function in Python?", "func", "def", "function", "lambda", "b"),
    (2, "What does len([1, 2, 3]) return?", "2", "3", "4", "Error", "b"),
    (2, "Which of these is a mutable data type in Python?", "tuple", "string", "list", "int", "c"),
    (3, "What will print(type([])) output?", "<class 'list'>", "<class 'array'>", "<class 'tuple'>", "Error", "a"),
    (3, "What does range(2, 10, 2) generate?", "2,4,6,8", "2,4,6,8,10", "2,3,4,...,9", "0,2,4,6,8", "a"),
    (4, "What is the output of print([1,2,3] + [4,5])?", "[1,2,3,4,5]", "Error", "[5,7,3]", "[1,2,3,[4,5]]", "a"),
    (4, "What does a try/except block handle?", "Loops", "Exceptions", "Comments", "Imports", "b"),
    (5, "What is a decorator in Python?", "A design pattern for styling console output", "A function that modifies another function's behavior", "A type of loop", "A built-in data type", "b"),
    (5, "What does *args allow a function to accept?", "A fixed number of arguments", "A variable number of positional arguments", "Only keyword arguments", "Only one argument", "b"),
],

"Data_Structures": [
    (1, "Which data structure follows LIFO (Last In, First Out)?", "Queue", "Stack", "Array", "Tree", "b"),
    (2, "What is the time complexity of accessing an element in an array by index?", "O(1)", "O(n)", "O(log n)", "O(n^2)", "a"),
    (2, "Which data structure follows FIFO (First In, First Out)?", "Stack", "Queue", "Tree", "Graph", "b"),
    (2, "A linked list node is typically composed of:", "Only data", "Only a pointer", "Data and a pointer to the next node", "Two pointers only", "c"),
    (2, "What is the main advantage of a linked list over an array?", "Faster indexing", "Dynamic size without shifting elements", "Always uses less memory", "Better cache performance", "b"),
    (3, "What is the time complexity of searching in a balanced binary search tree?", "O(1)", "O(n)", "O(log n)", "O(n^2)", "c"),
    (3, "In a binary tree, what is a leaf node?", "The root node", "A node with no children", "A node with exactly one child", "Any internal node", "b"),
    (4, "What is the worst-case time complexity of Quicksort?", "O(n log n)", "O(n)", "O(n^2)", "O(log n)", "c"),
    (4, "Which traversal visits the root before its left and right children?", "Inorder", "Postorder", "Preorder", "None of these", "c"),
    (4, "What is the space complexity of an adjacency matrix for a graph with V vertices?", "O(V)", "O(V^2)", "O(V log V)", "O(1)", "b"),
    (5, "What is the time complexity of inserting into a min-heap?", "O(1)", "O(log n)", "O(n)", "O(n log n)", "b"),
    (5, "Which data structure is best suited for implementing a priority queue?", "Array", "Stack", "Heap", "Linked list", "c"),
],

"Statistics": [
    (1, "What is the mean of 2, 4, 6, 8?", "4", "5", "6", "20", "b"),
    (2, "What is the mode of 2, 3, 3, 4, 5?", "2", "3", "4", "5", "b"),
    (3, "What does standard deviation measure?", "Central tendency", "Spread of data around the mean", "Total sum", "Median position", "b"),
    (3, "What is the median of 3, 7, 9, 15, 20?", "7", "9", "15", "10.8", "b"),
    (3, "What is the probability of rolling a 4 on a fair six-sided die?", "1/2", "1/3", "1/6", "1/4", "c"),
    (3, "If two events are mutually exclusive, what is P(A and B)?", "P(A) x P(B)", "P(A) + P(B)", "0", "1", "c"),
    (4, "What does a correlation coefficient of -0.9 indicate?", "No relationship", "Strong positive relationship", "Strong negative relationship", "Weak negative relationship", "c"),
    (4, "In a normal distribution, about what percentage of data falls within 1 standard deviation of the mean?", "50%", "68%", "95%", "99.7%", "b"),
    (4, "What is variance?", "The square root of standard deviation", "The average of the data", "The average of squared deviations from the mean", "The middle value of a dataset", "c"),
    (4, "What does a p-value less than 0.05 typically suggest in hypothesis testing?", "Accept the null hypothesis", "Reject the null hypothesis", "The sample size is too small", "The data is normally distributed", "b"),
    (5, "What is Bayes' Theorem used for?", "Calculating the mean of a dataset", "Updating probability estimates based on new evidence", "Measuring the spread of data", "Finding the mode", "b"),
    (5, "What does a confidence interval represent?", "The exact value of a population parameter", "A range of plausible values for a population parameter", "The required sample size", "The p-value of a test", "b"),
],

"AI_Basics": [
    (1, "What does AI stand for?", "Automated Interface", "Artificial Intelligence", "Advanced Integration", "Algorithmic Inference", "b"),
    (1, "Which of these is an example of a rule-based (non-learning) AI system?", "A chess engine using a fixed set of if-then rules", "A neural network trained on images", "A recommendation system trained on user data", "A model that learns from feedback", "a"),
    (1, "What is a 'search algorithm' used for in AI?", "Formatting code", "Finding a path or solution within a problem space", "Compressing files", "Encrypting data", "b"),
    (3, "What is an intelligent agent in AI?", "A human operator", "Anything that perceives its environment and acts to achieve goals", "A type of database", "A programming language", "b"),
    (3, "What does the A* search algorithm use to find the optimal path?", "Random guessing", "A heuristic function combined with path cost", "Only depth-first search", "Brute force with no heuristic", "b"),
    (3, "What is knowledge representation in AI?", "Storing raw video files", "Encoding facts and relationships so a system can reason about them", "Compressing neural network weights", "A type of hardware acceleration", "b"),
    (3, "What distinguishes a goal-based agent from a simple reflex agent?", "Goal-based agents consider future consequences of actions", "Simple reflex agents are always more accurate", "There is no difference", "Goal-based agents don't perceive the environment", "a"),
    (4, "What is the difference between breadth-first search and depth-first search?", "BFS explores level by level, DFS explores as far as possible along a branch first", "They are identical algorithms", "DFS always finds the shortest path, BFS doesn't", "BFS uses a stack, DFS uses a queue", "a"),
    (4, "What is the 'frame problem' in AI?", "A bug in image processing", "The challenge of representing what changes and stays the same after an action", "A hardware limitation", "A networking issue", "b"),
    (4, "In game-playing AI, what does the minimax algorithm assume?", "Both players play randomly", "One player maximizes and the other minimizes, both playing optimally", "Only one player is active", "The game has no opponent", "b"),
    (4, "What is alpha-beta pruning used for?", "Speeding up search by skipping branches that won't affect the decision", "Compressing neural networks", "Cleaning training data", "Normalizing input features", "a"),
    (5, "What key limitation led to the 'AI winters' in AI history?", "Lack of internet access", "Overpromising capabilities relative to available computation and data", "Too much available data", "Excessive government funding", "b"),
],

"ML": [
    (1, "What is supervised learning?", "Learning from labeled data with known outputs", "Learning with no data at all", "Learning only from rewards", "Learning without any algorithm", "a"),
    (1, "What is unsupervised learning typically used for?", "Predicting labels for labeled data", "Finding patterns or structure in unlabeled data", "Playing games against an opponent", "Only image classification", "b"),
    (2, "What is 'overfitting' in machine learning?", "The model performs well on training data but poorly on new data", "The model is too simple to learn patterns", "The model trains too quickly", "The model uses too little data", "a"),
    (2, "Why do we split data into training and test sets?", "To make the dataset larger", "To evaluate how well the model generalizes to unseen data", "To speed up training only", "It's not necessary", "b"),
    (2, "What is a loss function in machine learning?", "A function that measures how far predictions are from actual values", "A function that generates new data", "A type of neural network layer", "A hardware component", "a"),
    (2, "What type of problem is predicting a continuous numeric value (like house price)?", "Classification", "Regression", "Clustering", "Reinforcement learning", "b"),
    (3, "What does gradient descent do?", "Randomly changes model parameters", "Iteratively adjusts parameters to minimize the loss function", "Increases the loss function", "Deletes unnecessary training data", "b"),
    (3, "What is k-fold cross-validation used for?", "Speeding up inference", "More reliably estimating model performance across different data splits", "Reducing the number of features", "Increasing overfitting", "b"),
    (3, "What does regularization help prevent?", "Underfitting only", "Overfitting, by penalizing overly complex models", "Data leakage", "Class imbalance", "b"),
    (5, "What is the bias-variance tradeoff?", "Balancing model simplicity (bias) against sensitivity to training data (variance)", "A tradeoff between training speed and accuracy only", "A concept unrelated to model complexity", "Only relevant to deep learning", "a"),
    (5, "In ensemble learning, what does 'bagging' (e.g. Random Forest) primarily aim to reduce?", "Bias", "Variance, by averaging predictions from models trained on data subsets", "Training time", "Feature count", "b"),
    (5, "What does 'feature importance' in a Random Forest indicate?", "How much each input feature contributes to the model's predictions", "The order features were added to the dataset", "The correlation between two output labels", "The size of the training dataset", "a"),
],

"Neural_Networks": [
    (1, "What is a perceptron?", "A type of database", "The simplest artificial neural network unit, producing an output from weighted inputs", "A clustering algorithm", "A data preprocessing technique", "b"),
    (2, "What is an activation function used for in a neural network?", "Loading data into the model", "Introducing non-linearity so the network can learn complex patterns", "Removing outliers from data", "Splitting data into batches", "b"),
    (2, "Which of these is a commonly used activation function?", "ReLU", "SQL", "CSV", "API", "a"),
    (2, "What does a 'weight' represent in a neural network?", "The strength of a connection between two neurons", "The number of layers in the network", "The size of the training dataset", "The learning rate", "a"),
    (2, "What is a hidden layer?", "A layer that is not visible in code", "A layer between input and output where intermediate computation happens", "The output layer only", "A layer used only for data storage", "b"),
    (3, "What is backpropagation?", "A method for forwarding data through the network only", "The algorithm that computes gradients and updates weights by propagating error backward", "A way to visualize neural networks", "A type of activation function", "b"),
    (3, "What problem does ReLU help address compared to sigmoid?", "It eliminates the need for training", "It helps reduce the vanishing gradient problem in deep networks", "It always increases the loss", "It removes the need for weights", "b"),
    (4, "What is the 'learning rate' in gradient-based training?", "The number of training examples", "A hyperparameter controlling how large a step is taken when updating weights", "The number of layers in the network", "The accuracy of the model", "b"),
    (5, "What does batch normalization do?", "Normalizes inputs to a layer to stabilize and speed up training", "Removes layers from the network", "Increases the batch size automatically", "Only applies to the output layer", "a"),
    (5, "What is the vanishing gradient problem?", "Gradients become too large and cause instability", "Gradients become very small in early layers during backpropagation, slowing learning", "The model has no gradients at all", "A problem only in shallow networks", "b"),
    (5, "What does dropout do during training?", "Deletes training data permanently", "Randomly deactivates a fraction of neurons to reduce overfitting", "Increases the learning rate", "Adds more layers to the network", "b"),
    (5, "Why are deeper networks generally more expressive than shallow ones (given enough data)?", "They have fewer parameters", "They represent complex, hierarchical patterns through composed non-linear transformations", "They always train faster", "They never overfit", "b"),
],

"CNN": [
    (1, "What does CNN stand for?", "Central Neural Network", "Convolutional Neural Network", "Combined Node Network", "Cyclic Neural Network", "b"),
    (1, "What type of data are CNNs most commonly used for?", "Tabular spreadsheets", "Images", "Plain text only", "Audio waveforms only", "b"),
    (1, "What is a 'filter' (or kernel) in a CNN?", "A small matrix that slides over the input to detect patterns like edges", "A layer that removes noise from labels", "A method to split training data", "A type of loss function", "a"),
    (2, "What is the purpose of a pooling layer in a CNN?", "To increase the image resolution", "To reduce the spatial dimensions of the feature map while retaining key information", "To add color to grayscale images", "To label the training data", "b"),
    (2, "What does 'max pooling' do?", "Takes the average value in a region", "Takes the maximum value in a region of the feature map", "Removes the region entirely", "Multiplies all values in a region", "b"),
    (2, "What is 'stride' in a CNN?", "The number of layers in the network", "The step size the filter moves across the input", "The size of the output image", "The number of training epochs", "b"),
    (3, "Why do CNNs use shared weights (the same filter) across an image?", "To reduce parameters and detect the same feature anywhere in the image", "To increase training time", "To make the model memorize the training set", "It has no real benefit", "a"),
    (3, "What does a deeper CNN layer typically learn compared to an early layer?", "Only simple edges, same as early layers", "More abstract, complex features built from simpler ones detected earlier", "Nothing different", "Only color information", "b"),
    (4, "What is 'padding' used for in a CNN?", "To make training slower on purpose", "To preserve the spatial dimensions of the input after convolution", "To remove the color channels", "To increase the batch size", "b"),
    (5, "What is 'transfer learning' in the context of CNNs?", "Moving a model to a different programming language", "Using a model pretrained on one large dataset as a starting point for a related task", "Transferring data between two servers", "Converting images to grayscale", "b"),
    (5, "What issue can occur if a CNN's receptive field is too small?", "The model may fail to capture larger patterns or context in the image", "The model will always overfit", "Training will be too fast", "It has no effect on performance", "a"),
    (5, "What is the main advantage of CNNs over fully-connected networks for image tasks?", "They require more parameters", "They exploit spatial locality and weight sharing, needing far fewer parameters", "They cannot use backpropagation", "They only work on grayscale images", "b"),
],

"RNN": [
    (1, "What does RNN stand for?", "Rapid Neural Network", "Recurrent Neural Network", "Reduced Node Network", "Randomized Neural Network", "b"),
    (1, "What type of data are RNNs best suited for?", "Sequential data like text or time series", "Single static images", "Unordered tabular data only", "Random noise", "a"),
    (2, "What is the 'hidden state' in an RNN?", "A layer that is never used", "A memory that carries information from previous time steps forward", "The final output layer only", "A type of activation function", "b"),
    (2, "Why can't a standard feedforward network handle sequences well?", "It has no concept of order or memory between inputs", "It's too slow", "It only works with images", "It has too many parameters", "a"),
    (2, "What does an RNN do at each time step?", "Processes the current input along with the hidden state from the previous step", "Ignores all previous inputs", "Trains a completely new model", "Only outputs random values", "a"),
    (2, "What is a common application of RNNs?", "Image compression", "Language modeling and text generation", "Sorting algorithms", "Database indexing", "b"),
    (3, "The vanishing gradient problem is particularly severe for RNNs on:", "Very short sequences only", "Long sequences, where gradients shrink over many time steps", "Single time-step data", "It never happens in RNNs", "b"),
    (3, "What is 'Backpropagation Through Time' (BPTT)?", "A way to run RNNs faster", "The algorithm for training RNNs by unrolling them across time steps", "A method for image classification", "A type of pooling operation", "b"),
    (4, "What is a bidirectional RNN?", "An RNN that processes the sequence in both forward and backward directions", "An RNN with two separate outputs only", "An RNN that can only be used for images", "An RNN with no hidden state", "a"),
    (4, "Why do standard RNNs struggle with long-term dependencies?", "They have too much memory", "Information from early steps gets diluted as gradients vanish over long sequences", "They only process one word at a time", "They cannot be trained at all", "b"),
    (5, "What motivated the development of gated architectures like LSTM and GRU?", "To make RNNs simpler", "To address the vanishing gradient problem and capture long-term dependencies", "To eliminate the need for hidden states", "To replace CNNs entirely", "b"),
    (5, "What is 'teacher forcing' in sequence model training?", "Forcing the model to only use its own previous predictions", "Using the ground-truth previous output as input at the next time step during training", "A regularization technique unrelated to sequences", "A method to compress the network", "b"),
],

"LSTM": [
    (1, "What does LSTM stand for?", "Long Short-Term Memory", "Linear Sequential Training Model", "Layered System for Time Modeling", "Large Scale Training Method", "a"),
    (1, "What problem was LSTM specifically designed to solve?", "Image classification", "The vanishing gradient problem in standard RNNs for long sequences", "Overfitting in CNNs", "Slow training in decision trees", "b"),
    (2, "What is the 'cell state' in an LSTM?", "A separate memory pathway allowing information to persist over long distances", "The final output of the network", "A type of activation function only", "The input layer", "a"),
    (2, "How many main gates does a standard LSTM cell have?", "1", "2", "3", "5", "c"),
    (3, "What is the role of the 'forget gate' in an LSTM?", "Decides what information to discard from the cell state", "Generates the final prediction", "Increases the learning rate", "Adds new layers to the network", "a"),
    (4, "What is the role of the 'input gate' in an LSTM?", "Decides what new information to add to the cell state", "Deletes the entire cell state", "Controls the batch size", "Has no functional role", "a"),
    (4, "What is the role of the 'output gate' in an LSTM?", "Controls what part of the cell state is exposed as output at that time step", "Discards old information only", "Adjusts the learning rate", "Selects the training data", "a"),
    (4, "Compared to a standard RNN, why can LSTMs better retain long-range information?", "They have more layers only", "The gated cell state lets information flow mostly unchanged unless gates modify it", "They don't use backpropagation", "They process the entire sequence at once, ignoring order", "b"),
    (4, "What is a key computational trade-off of LSTMs compared to simple RNNs?", "LSTMs are computationally cheaper due to fewer parameters", "LSTMs have more parameters and are costlier due to gating mechanisms", "LSTMs cannot be trained with backpropagation", "LSTMs cannot process sequences", "b"),
    (5, "How does a GRU differ from an LSTM?", "GRUs have no gates at all", "GRUs merge the forget/input gates into an update gate and combine cell/hidden states", "GRUs are only used for images", "GRUs cannot handle sequences", "b"),
    (5, "When might an LSTM still underperform compared to a Transformer-based model?", "Never, LSTMs are always better", "On very long sequences, where attention captures long-range dependencies more directly", "On short sequences only", "LSTMs cannot be compared to Transformers", "b"),
    (5, "Why is initializing the forget gate bias to a positive value a common practice?", "It has no effect on training", "It encourages the network to remember information by default early in training", "It forces the network to forget everything immediately", "It changes the network into a CNN", "b"),
],

"NLP": [
    (1, "What does NLP stand for?", "Natural Language Processing", "Neural Language Program", "Numerical Language Prediction", "Node Level Processing", "a"),
    (1, "What is 'tokenization' in NLP?", "Encrypting text data", "Breaking text into smaller units like words or subwords", "Translating text into another language", "Removing all punctuation permanently", "b"),
    (1, "What is a common application of NLP?", "Image classification", "Machine translation and chatbots", "Sorting numerical arrays", "3D rendering", "b"),
    (1, "What does 'stop word removal' typically refer to?", "Removing common, low-information words like 'the' or 'is'", "Removing all nouns from a sentence", "Deleting the entire dataset", "Removing punctuation only", "a"),
    (2, "What is a 'word embedding'?", "A dense vector representation of a word that captures semantic meaning", "A random string assigned to each word", "A type of image filter", "A way to compress audio files", "a"),
    (2, "What does 'stemming' do in text preprocessing?", "Adds new words to a sentence", "Reduces a word to its root/base form, often crudely (e.g. running -> run)", "Translates text to another language", "Removes stop words only", "b"),
    (2, "What is 'part-of-speech tagging'?", "Labeling each word with its grammatical role (noun, verb, etc.)", "Translating parts of a sentence", "Counting the number of sentences", "Removing duplicate words", "a"),
    (3, "What is the key idea behind Word2Vec?", "Words with similar meanings tend to appear in similar contexts, getting similar vectors", "Every word gets a completely random vector", "It only works for single-letter words", "It replaces words with images", "a"),
    (3, "What is 'named entity recognition' (NER)?", "Identifying and classifying proper nouns like names, places, and organizations", "Removing named entities from a document", "Translating names into another language", "Counting the number of words in a sentence", "a"),
    (3, "Why are word embeddings generally better than one-hot encoding for words?", "One-hot vectors are dense and small; embeddings are sparse and huge", "Embeddings are dense, lower-dimensional, and capture semantic similarity", "One-hot encoding already captures meaning", "There is no real difference", "b"),
    (3, "What is the purpose of an attention mechanism in NLP models?", "To let the model focus on the most relevant parts of the input for each output", "To randomly drop words from the input", "To speed up tokenization only", "To remove the need for embeddings", "a"),
    (5, "What key architectural innovation do Transformer models use instead of recurrence?", "Convolutional filters only", "Self-attention, weighing relationships between all tokens in parallel", "Simple lookup tables", "Random sampling of words", "b"),
],
}


def build_lookup():
    """Turn REAL_QUESTIONS into {(topic, difficulty): [question dicts in order]}"""
    lookup = {}
    for topic, items in REAL_QUESTIONS.items():
        for diff, text, a, b, c, d, correct in items:
            key = (topic, diff)
            lookup.setdefault(key, []).append({
                "question_text": text,
                "option_a": a, "option_b": b, "option_c": c, "option_d": d,
                "correct_option": correct,
            })
    return lookup


if __name__ == "__main__":
    questions = pd.read_csv(QUESTIONS_CSV)
    lookup = build_lookup()
    pointer = {key: 0 for key in lookup}  # tracks how many we've assigned per (topic, difficulty)

    missing = []
    for idx, row in questions.iterrows():
        key = (row["topic"], row["difficulty"])
        bank = lookup.get(key)
        if bank is None or pointer[key] >= len(bank):
            missing.append((row["question_id"], key))
            continue
        real_q = bank[pointer[key]]
        pointer[key] += 1
        questions.loc[idx, "question_text"] = real_q["question_text"]
        questions.loc[idx, "option_a"] = real_q["option_a"]
        questions.loc[idx, "option_b"] = real_q["option_b"]
        questions.loc[idx, "option_c"] = real_q["option_c"]
        questions.loc[idx, "option_d"] = real_q["option_d"]
        questions.loc[idx, "correct_option"] = real_q["correct_option"]

    if missing:
        print(f"WARNING: {len(missing)} rows had no matching real question and were left as placeholders:")
        for qid, key in missing:
            print(f"  {qid}  (topic={key[0]}, difficulty={key[1]})")
    else:
        print(f"All {len(questions)} rows successfully populated with real questions.")

    questions.to_csv(QUESTIONS_CSV, index=False)
    print(f"Saved -> {QUESTIONS_CSV}")
