<?php
/**
 * 扩展的单词列表 - 每个年级100+单词
 * 基于人教版教材和常用词汇整理
 */

function getWordLists() {
    return [
    'grade1' => [
        // 基础问候和礼貌用语
        'hello', 'hi', 'good', 'thank', 'thanks', 'yes', 'no', 'please', 'sorry', 'bye', 'goodbye',
        'morning', 'afternoon', 'evening', 'night', 'day', 'week', 'month', 'year', 'today', 'tomorrow', 'yesterday',
        // 食物
        'apple', 'banana', 'orange', 'water', 'milk', 'bread', 'rice', 'egg', 'fish', 'chicken',
        'cake', 'cookie', 'juice', 'tea', 'coffee', 'meat', 'vegetable', 'fruit', 'food', 'dinner',
        'lunch', 'breakfast', 'snack', 'candy', 'ice', 'cream', 'pizza', 'noodle', 'soup', 'sandwich',
        // 数字
        'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
        'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'twenty', 'thirty', 'hundred',
        // 颜色
        'red', 'blue', 'green', 'yellow', 'black', 'white', 'pink', 'purple', 'brown', 'orange',
        'gray', 'grey', 'color', 'colour',
        // 身体部位
        'head', 'eye', 'eyes', 'nose', 'mouth', 'ear', 'ears', 'hand', 'hands', 'foot', 'feet',
        'leg', 'legs', 'arm', 'arms', 'face', 'hair', 'tooth', 'teeth', 'finger', 'fingers',
        // 家庭成员
        'father', 'mother', 'dad', 'mom', 'brother', 'sister', 'baby', 'family', 'grandpa', 'grandma',
        'uncle', 'aunt', 'cousin', 'son', 'daughter',
        // 动物
        'cat', 'dog', 'bird', 'fish', 'rabbit', 'duck', 'chicken', 'pig', 'cow', 'horse',
        'elephant', 'tiger', 'lion', 'monkey', 'panda', 'bear', 'sheep', 'goat', 'mouse', 'snake',
        // 学校用品
        'book', 'books', 'pen', 'pens', 'pencil', 'pencils', 'bag', 'school', 'teacher', 'student',
        'class', 'desk', 'chair', 'ruler', 'eraser', 'crayon', 'marker', 'notebook', 'backpack',
        // 动作
        'run', 'runs', 'jump', 'jumps', 'walk', 'walks', 'sit', 'sits', 'stand', 'stands',
        'eat', 'eats', 'drink', 'drinks', 'sleep', 'sleeps', 'play', 'plays', 'sing', 'sings',
        'dance', 'dances', 'read', 'reads', 'write', 'writes', 'draw', 'draws', 'swim', 'swims',
        // 其他
        'toy', 'toys', 'ball', 'balls', 'car', 'cars', 'bus', 'buses', 'house', 'room', 'rooms',
        'door', 'doors', 'window', 'windows', 'bed', 'beds', 'table', 'tables', 'chair', 'chairs',
        'box', 'boxes', 'cup', 'cups', 'plate', 'plates', 'spoon', 'spoons', 'fork', 'forks'
    ],
    
    'grade2' => [
        // 学校相关
        'book', 'pen', 'pencil', 'school', 'teacher', 'student', 'class', 'desk', 'chair', 'bag',
        'homework', 'lesson', 'subject', 'math', 'english', 'chinese', 'art', 'music', 'sport', 'game',
        'library', 'playground', 'gym', 'cafeteria', 'office', 'principal', 'classmate', 'friend', 'friends',
        // 家庭成员扩展
        'friend', 'friends', 'family', 'father', 'mother', 'brother', 'sister', 'grandfather', 'grandmother',
        'uncle', 'aunt', 'cousin', 'son', 'daughter', 'parent', 'parents', 'child', 'children', 'people',
        'man', 'men', 'woman', 'women', 'boy', 'boys', 'girl', 'girls', 'baby', 'babies',
        // 动物扩展
        'dog', 'dogs', 'cat', 'cats', 'bird', 'birds', 'rabbit', 'rabbits', 'elephant', 'elephants',
        'tiger', 'tigers', 'lion', 'lions', 'monkey', 'monkeys', 'panda', 'pandas', 'bear', 'bears',
        'sheep', 'goat', 'goats', 'duck', 'ducks', 'chicken', 'chickens', 'cow', 'cows', 'horse', 'horses',
        'pig', 'pigs', 'mouse', 'mice', 'snake', 'snakes', 'frog', 'frogs', 'turtle', 'turtles',
        // 身体部位扩展
        'body', 'bodies', 'head', 'heads', 'hair', 'eye', 'eyes', 'ear', 'ears', 'nose', 'noses',
        'mouth', 'mouths', 'tooth', 'teeth', 'hand', 'hands', 'finger', 'fingers', 'arm', 'arms',
        'leg', 'legs', 'foot', 'feet', 'knee', 'knees', 'shoulder', 'shoulders', 'back', 'backs',
        'neck', 'necks', 'face', 'faces', 'toe', 'toes', 'thumb', 'thumbs',
        // 食物扩展
        'breakfast', 'lunch', 'dinner', 'food', 'fruit', 'fruits', 'vegetable', 'vegetables', 'meat', 'rice',
        'noodle', 'noodles', 'soup', 'cake', 'cakes', 'candy', 'candies', 'chocolate', 'ice', 'cream',
        'sandwich', 'sandwiches', 'hamburger', 'hamburgers', 'pizza', 'salad', 'salads', 'bread', 'butter',
        'cheese', 'milk', 'juice', 'water', 'tea', 'coffee', 'sugar', 'salt', 'pepper',
        // 服装
        'clothes', 'shirt', 'shirts', 'dress', 'dresses', 'skirt', 'skirts', 'pants', 'shoes', 'socks',
        'hat', 'hats', 'coat', 'coats', 'jacket', 'jackets', 'sweater', 'sweaters', 'gloves', 'scarf',
        // 天气
        'weather', 'sun', 'rain', 'wind', 'cloud', 'clouds', 'snow', 'sunny', 'rainy', 'cloudy',
        'windy', 'snowy', 'storm', 'storms', 'rainbow', 'rainbows', 'hot', 'cold', 'warm', 'cool',
        // 时间
        'time', 'clock', 'clocks', 'hour', 'hours', 'minute', 'minutes', 'second', 'seconds',
        'morning', 'afternoon', 'evening', 'night', 'day', 'days', 'week', 'weeks', 'month', 'months',
        'year', 'years', 'today', 'tomorrow', 'yesterday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
        // 其他
        'toy', 'toys', 'doll', 'dolls', 'ball', 'balls', 'kite', 'kites', 'bike', 'bikes',
        'car', 'cars', 'bus', 'buses', 'train', 'trains', 'plane', 'planes', 'ship', 'ships',
        'boat', 'boats', 'truck', 'trucks', 'taxi', 'taxis', 'subway', 'subways'
    ],
    
    'grade3' => [
        // 情感和状态
        'happy', 'sad', 'angry', 'tired', 'hungry', 'thirsty', 'hot', 'cold', 'warm', 'cool',
        'excited', 'worried', 'afraid', 'surprised', 'proud', 'shy', 'brave', 'kind', 'nice', 'friendly',
        'sick', 'healthy', 'well', 'fine', 'okay', 'ok', 'great', 'wonderful', 'terrible', 'awful',
        // 形容词
        'big', 'small', 'tall', 'short', 'long', 'new', 'old', 'young', 'beautiful', 'ugly',
        'good', 'bad', 'great', 'wonderful', 'terrible', 'easy', 'hard', 'difficult', 'simple', 'complex',
        'clean', 'dirty', 'full', 'empty', 'heavy', 'light', 'fast', 'slow', 'quick', 'quiet',
        'loud', 'soft', 'high', 'low', 'wide', 'narrow', 'thick', 'thin', 'strong', 'weak',
        'rich', 'poor', 'expensive', 'cheap', 'free', 'busy', 'free', 'ready', 'sure', 'certain',
        // 颜色扩展
        'red', 'blue', 'green', 'yellow', 'black', 'white', 'orange', 'pink', 'purple', 'brown',
        'gray', 'grey', 'gold', 'silver', 'color', 'colour', 'bright', 'dark', 'light', 'colorful',
        // 动作扩展
        'play', 'plays', 'read', 'reads', 'write', 'writes', 'draw', 'draws', 'sing', 'sings',
        'dance', 'dances', 'run', 'runs', 'jump', 'jumps', 'walk', 'walks', 'swim', 'swims',
        'eat', 'eats', 'drink', 'drinks', 'sleep', 'sleeps', 'wake', 'wakes', 'study', 'studies',
        'learn', 'learns', 'teach', 'teaches', 'help', 'helps', 'work', 'works', 'rest', 'rests',
        'think', 'thinks', 'know', 'knows', 'understand', 'understands', 'remember', 'remembers', 'forget', 'forgets',
        'see', 'sees', 'look', 'looks', 'watch', 'watches', 'listen', 'listens', 'hear', 'hears',
        'speak', 'speaks', 'talk', 'talks', 'say', 'says', 'tell', 'tells', 'ask', 'asks',
        'answer', 'answers', 'call', 'calls', 'shout', 'shouts', 'cry', 'cries', 'laugh', 'laughs',
        'smile', 'smiles', 'come', 'comes', 'go', 'goes', 'leave', 'leaves', 'arrive', 'arrives',
        'return', 'returns', 'enter', 'enters', 'exit', 'exits', 'move', 'moves', 'stop', 'stops',
        'start', 'starts', 'finish', 'finishes', 'begin', 'begins', 'end', 'ends', 'open', 'opens',
        'close', 'closes', 'buy', 'buys', 'sell', 'sells', 'give', 'gives', 'take', 'takes',
        'get', 'gets', 'put', 'puts', 'bring', 'brings', 'send', 'sends', 'receive', 'receives',
        // 地点
        'place', 'places', 'home', 'homes', 'house', 'houses', 'room', 'rooms', 'bedroom', 'bedrooms',
        'kitchen', 'kitchens', 'bathroom', 'bathrooms', 'garden', 'gardens', 'park', 'parks', 'zoo', 'zoos',
        'library', 'libraries', 'hospital', 'hospitals', 'school', 'schools', 'shop', 'shops', 'store', 'stores',
        'market', 'markets', 'restaurant', 'restaurants', 'hotel', 'hotels', 'bank', 'banks', 'post', 'post',
        'office', 'offices', 'classroom', 'classrooms', 'playground', 'playgrounds', 'cafeteria', 'cafeterias',
        'city', 'cities', 'town', 'towns', 'village', 'villages', 'country', 'countries', 'street', 'streets',
        'road', 'roads', 'bridge', 'bridges', 'building', 'buildings', 'tower', 'towers',
        // 交通工具
        'transport', 'car', 'cars', 'bus', 'buses', 'train', 'trains', 'plane', 'planes', 'ship', 'ships',
        'bike', 'bikes', 'bicycle', 'bicycles', 'taxi', 'taxis', 'subway', 'subways', 'boat', 'boats',
        'truck', 'trucks', 'motorcycle', 'motorcycles', 'helicopter', 'helicopters',
        // 自然
        'nature', 'tree', 'trees', 'flower', 'flowers', 'grass', 'sky', 'sun', 'moon', 'star', 'stars',
        'cloud', 'clouds', 'rain', 'snow', 'wind', 'storm', 'storms', 'rainbow', 'rainbows',
        'mountain', 'mountains', 'river', 'rivers', 'lake', 'lakes', 'ocean', 'oceans', 'beach', 'beaches',
        'forest', 'forests', 'island', 'islands', 'desert', 'deserts', 'valley', 'valleys', 'hill', 'hills'
    ],
    
    'grade4' => [
        // 动作动词扩展
        'play', 'read', 'write', 'draw', 'sing', 'dance', 'run', 'jump', 'walk', 'swim',
        'eat', 'drink', 'sleep', 'wake', 'study', 'learn', 'teach', 'help', 'work', 'rest',
        'think', 'know', 'understand', 'remember', 'forget', 'see', 'look', 'watch', 'listen', 'hear',
        'speak', 'talk', 'say', 'tell', 'ask', 'answer', 'question', 'call', 'shout', 'whisper',
        'come', 'go', 'leave', 'arrive', 'return', 'enter', 'exit', 'move', 'stop', 'start',
        'finish', 'complete', 'continue', 'break', 'fix', 'repair', 'build', 'make', 'create', 'design',
        'cook', 'clean', 'wash', 'brush', 'comb', 'wear', 'dress', 'undress', 'change', 'choose',
        'decide', 'plan', 'prepare', 'organize', 'manage', 'control', 'improve', 'develop', 'grow', 'change',
        'save', 'spend', 'pay', 'cost', 'buy', 'sell', 'trade', 'exchange', 'borrow', 'lend',
        'find', 'search', 'look', 'discover', 'explore', 'visit', 'travel', 'tour', 'trip', 'journey',
        // 地点扩展
        'house', 'room', 'bedroom', 'kitchen', 'bathroom', 'garden', 'park', 'zoo', 'library', 'hospital',
        'school', 'classroom', 'office', 'shop', 'store', 'market', 'restaurant', 'hotel', 'bank', 'post',
        'city', 'town', 'village', 'country', 'countryside', 'street', 'road', 'bridge', 'building', 'tower',
        'museum', 'theater', 'cinema', 'stadium', 'airport', 'station', 'harbor', 'port', 'beach', 'coast',
        'mountain', 'hill', 'valley', 'river', 'lake', 'ocean', 'sea', 'island', 'forest', 'desert',
        // 职业
        'job', 'work', 'worker', 'teacher', 'doctor', 'nurse', 'driver', 'cook', 'farmer', 'worker',
        'policeman', 'policewoman', 'fireman', 'pilot', 'soldier', 'engineer', 'scientist', 'artist', 'writer', 'singer',
        'dancer', 'actor', 'actress', 'musician', 'painter', 'photographer', 'journalist', 'reporter', 'lawyer', 'judge',
        'manager', 'director', 'president', 'mayor', 'mayor', 'secretary', 'assistant', 'clerk', 'cashier', 'waiter',
        'waitress', 'chef', 'baker', 'butcher', 'barber', 'hairdresser', 'dentist', 'veterinarian', 'vet', 'mechanic',
        // 学科
        'subject', 'lesson', 'class', 'math', 'english', 'chinese', 'science', 'history', 'geography', 'art',
        'music', 'sport', 'pe', 'computer', 'technology', 'physics', 'chemistry', 'biology', 'politics', 'philosophy',
        'literature', 'language', 'grammar', 'vocabulary', 'spelling', 'reading', 'writing', 'listening', 'speaking',
        // 时间扩展
        'time', 'clock', 'watch', 'hour', 'minute', 'second', 'morning', 'afternoon', 'evening', 'night',
        'day', 'week', 'month', 'year', 'today', 'tomorrow', 'yesterday', 'monday', 'tuesday', 'wednesday',
        'thursday', 'friday', 'saturday', 'sunday', 'weekend', 'weekday', 'holiday', 'vacation', 'break',
        // 季节和月份
        'season', 'spring', 'summer', 'autumn', 'winter', 'january', 'february', 'march', 'april', 'may',
        'june', 'july', 'august', 'september', 'october', 'november', 'december',
        // 天气和自然现象
        'weather', 'sunny', 'rainy', 'cloudy', 'windy', 'snowy', 'storm', 'thunder', 'lightning', 'fog',
        'temperature', 'degree', 'hot', 'cold', 'warm', 'cool', 'freezing', 'boiling', 'mild', 'extreme'
    ],
    
    'grade5' => [
        // 天气和自然
        'weather', 'sunny', 'rainy', 'cloudy', 'windy', 'snowy', 'storm', 'rainbow', 'season', 'spring',
        'summer', 'autumn', 'winter', 'holiday', 'vacation', 'travel', 'trip', 'journey', 'adventure', 'explore',
        'country', 'city', 'village', 'mountain', 'river', 'lake', 'ocean', 'beach', 'forest', 'island',
        'desert', 'valley', 'hill', 'field', 'farm', 'garden', 'park', 'zoo', 'museum', 'theater',
        'thunder', 'lightning', 'fog', 'mist', 'dew', 'frost', 'hail', 'sleet', 'drizzle', 'shower',
        // 地理
        'earth', 'world', 'continent', 'country', 'nation', 'capital', 'province', 'state', 'region', 'area',
        'north', 'south', 'east', 'west', 'direction', 'map', 'globe', 'geography', 'location', 'place',
        'border', 'boundary', 'coast', 'shore', 'beach', 'cliff', 'cave', 'volcano', 'earthquake', 'tsunami',
        'climate', 'temperature', 'humidity', 'pressure', 'altitude', 'latitude', 'longitude', 'equator', 'pole',
        // 环境
        'environment', 'nature', 'animal', 'plant', 'tree', 'flower', 'grass', 'leaf', 'root', 'branch',
        'sky', 'cloud', 'rain', 'snow', 'wind', 'sun', 'moon', 'star', 'planet', 'universe',
        'pollution', 'waste', 'garbage', 'trash', 'recycle', 'reuse', 'reduce', 'protect', 'conserve', 'preserve',
        'wildlife', 'species', 'habitat', 'ecosystem', 'balance', 'harmony', 'destruction', 'damage', 'restore', 'repair',
        // 活动
        'activity', 'sport', 'game', 'play', 'exercise', 'practice', 'competition', 'match', 'race', 'contest',
        'hobby', 'interest', 'fun', 'enjoy', 'like', 'love', 'hate', 'prefer', 'choose', 'decide',
        'swimming', 'running', 'jumping', 'climbing', 'cycling', 'skating', 'skiing', 'surfing', 'diving', 'fishing',
        'camping', 'hiking', 'picnic', 'barbecue', 'party', 'celebration', 'festival', 'ceremony', 'event', 'occasion',
        // 健康
        'health', 'healthy', 'ill', 'sick', 'doctor', 'hospital', 'medicine', 'drug', 'treatment', 'cure',
        'body', 'head', 'heart', 'lung', 'stomach', 'blood', 'bone', 'muscle', 'skin', 'hair',
        'brain', 'mind', 'thought', 'feeling', 'emotion', 'mood', 'spirit', 'soul', 'energy', 'strength',
        'exercise', 'fitness', 'diet', 'nutrition', 'vitamin', 'protein', 'calorie', 'weight', 'height', 'age',
        'pain', 'ache', 'fever', 'cough', 'sneeze', 'headache', 'stomachache', 'toothache', 'backache', 'sore',
        'medicine', 'pill', 'tablet', 'capsule', 'syrup', 'injection', 'vaccine', 'antibiotic', 'antibiotic', 'surgery'
    ],
    
    'grade6' => [
        // 学科和学习
        'science', 'math', 'history', 'geography', 'art', 'music', 'sport', 'game', 'hobby', 'interest',
        'subject', 'lesson', 'homework', 'exam', 'test', 'grade', 'score', 'result', 'success', 'fail',
        'study', 'learn', 'teach', 'education', 'knowledge', 'skill', 'ability', 'talent', 'gift', 'genius',
        'intelligence', 'wisdom', 'understanding', 'comprehension', 'memory', 'concentration', 'focus', 'attention',
        'exam', 'examination', 'test', 'quiz', 'assignment', 'project', 'report', 'essay', 'paper', 'thesis',
        'pass', 'fail', 'pass', 'excellent', 'good', 'average', 'poor', 'grade', 'mark', 'score',
        // 科技
        'computer', 'internet', 'email', 'website', 'phone', 'mobile', 'tablet', 'camera', 'video', 'photo',
        'technology', 'machine', 'robot', 'device', 'tool', 'equipment', 'appliance', 'gadget', 'invention', 'innovation',
        'software', 'hardware', 'program', 'application', 'app', 'website', 'webpage', 'browser', 'search', 'engine',
        'download', 'upload', 'file', 'folder', 'document', 'data', 'information', 'database', 'server', 'network',
        'digital', 'electronic', 'electric', 'battery', 'charge', 'power', 'energy', 'solar', 'wind', 'nuclear',
        // 社会
        'society', 'community', 'group', 'team', 'club', 'organization', 'company', 'business', 'industry', 'trade',
        'government', 'law', 'rule', 'regulation', 'policy', 'right', 'duty', 'responsibility', 'freedom', 'justice',
        'democracy', 'republic', 'monarchy', 'president', 'prime', 'minister', 'mayor', 'governor', 'senator', 'representative',
        'citizen', 'resident', 'population', 'people', 'nation', 'country', 'state', 'province', 'city', 'town',
        'economy', 'economic', 'money', 'currency', 'dollar', 'yuan', 'euro', 'pound', 'yen', 'rupee',
        'bank', 'account', 'save', 'spend', 'invest', 'investment', 'profit', 'loss', 'income', 'expense',
        // 文化
        'culture', 'tradition', 'custom', 'festival', 'celebration', 'ceremony', 'holiday', 'vacation', 'party', 'event',
        'language', 'word', 'sentence', 'paragraph', 'article', 'story', 'novel', 'poem', 'song', 'music',
        'dance', 'theater', 'drama', 'comedy', 'tragedy', 'opera', 'ballet', 'concert', 'performance', 'show',
        'art', 'painting', 'drawing', 'sculpture', 'statue', 'monument', 'museum', 'gallery', 'exhibition', 'display',
        'religion', 'belief', 'faith', 'god', 'goddess', 'temple', 'church', 'mosque', 'synagogue', 'prayer',
        // 媒体
        'media', 'news', 'newspaper', 'magazine', 'book', 'movie', 'film', 'television', 'radio', 'internet',
        'information', 'message', 'news', 'report', 'article', 'story', 'advertisement', 'commercial', 'program', 'show',
        'journalist', 'reporter', 'correspondent', 'editor', 'publisher', 'author', 'writer', 'poet', 'novelist', 'playwright',
        'broadcast', 'transmission', 'signal', 'channel', 'station', 'frequency', 'wavelength', 'antenna', 'receiver', 'transmitter'
    ],
    
    'grade7' => [
        // 形容词扩展
        'important', 'necessary', 'possible', 'impossible', 'difficult', 'easy', 'simple', 'complex', 'different', 'same',
        'special', 'common', 'normal', 'strange', 'interesting', 'boring', 'exciting', 'amazing', 'wonderful', 'terrible',
        'beautiful', 'ugly', 'pretty', 'handsome', 'attractive', 'charming', 'elegant', 'graceful', 'fashionable', 'modern',
        'ancient', 'old', 'new', 'young', 'fresh', 'stale', 'clean', 'dirty', 'tidy', 'messy',
        'bright', 'dark', 'light', 'heavy', 'thick', 'thin', 'wide', 'narrow', 'deep', 'shallow',
        'sharp', 'dull', 'smooth', 'rough', 'soft', 'hard', 'flexible', 'rigid', 'solid', 'liquid',
        'gas', 'empty', 'full', 'half', 'whole', 'complete', 'incomplete', 'perfect', 'imperfect', 'excellent',
        // 情感和态度
        'feeling', 'emotion', 'mood', 'attitude', 'opinion', 'view', 'thought', 'idea', 'belief', 'faith',
        'happy', 'sad', 'angry', 'excited', 'worried', 'afraid', 'surprised', 'proud', 'ashamed', 'embarrassed',
        'disappointed', 'satisfied', 'pleased', 'delighted', 'thrilled', 'ecstatic', 'miserable', 'depressed', 'lonely', 'isolated',
        'confident', 'shy', 'nervous', 'anxious', 'calm', 'relaxed', 'stressed', 'tired', 'exhausted', 'energetic',
        'hopeful', 'hopeless', 'optimistic', 'pessimistic', 'positive', 'negative', 'neutral', 'indifferent', 'curious', 'interested',
        // 决策和行动
        'decide', 'choose', 'plan', 'prepare', 'organize', 'manage', 'control', 'improve', 'develop', 'create',
        'build', 'make', 'do', 'finish', 'complete', 'achieve', 'succeed', 'fail', 'win', 'lose',
        'attempt', 'try', 'effort', 'struggle', 'challenge', 'obstacle', 'difficulty', 'problem', 'solution', 'resolve',
        'goal', 'aim', 'target', 'purpose', 'intention', 'motive', 'reason', 'cause', 'effect', 'result',
        'opportunity', 'chance', 'luck', 'fortune', 'success', 'achievement', 'accomplishment', 'victory', 'triumph', 'defeat',
        // 关系
        'relationship', 'friend', 'friendship', 'enemy', 'stranger', 'neighbor', 'colleague', 'partner', 'companion', 'mate',
        'love', 'like', 'hate', 'dislike', 'respect', 'admire', 'trust', 'believe', 'doubt', 'suspect',
        'care', 'concern', 'worry', 'anxiety', 'fear', 'hope', 'wish', 'dream', 'desire', 'want',
        'need', 'require', 'demand', 'request', 'ask', 'beg', 'plead', 'insist', 'persist', 'persevere',
        // 问题解决
        'problem', 'question', 'answer', 'solution', 'method', 'way', 'means', 'approach', 'strategy', 'tactic',
        'help', 'support', 'assist', 'aid', 'rescue', 'save', 'protect', 'defend', 'guard', 'shelter',
        'solve', 'resolve', 'fix', 'repair', 'mend', 'restore', 'recover', 'heal', 'cure', 'treat',
        'prevent', 'avoid', 'escape', 'flee', 'hide', 'seek', 'search', 'find', 'discover', 'explore'
    ],
    
    'grade8' => [
        // 环境和社会
        'environment', 'pollution', 'protect', 'recycle', 'waste', 'energy', 'resource', 'nature', 'wildlife', 'species',
        'culture', 'tradition', 'custom', 'festival', 'celebration', 'ceremony', 'religion', 'belief', 'value', 'respect',
        'society', 'community', 'population', 'government', 'law', 'right', 'duty', 'responsibility', 'freedom', 'justice',
        'climate', 'change', 'global', 'warming', 'greenhouse', 'effect', 'carbon', 'dioxide', 'emission', 'reduction',
        'conservation', 'preservation', 'sustainability', 'renewable', 'solar', 'wind', 'hydroelectric', 'geothermal', 'biomass',
        'deforestation', 'reforestation', 'biodiversity', 'extinction', 'endangered', 'habitat', 'destruction', 'restoration', 'recovery',
        // 经济
        'economy', 'economic', 'money', 'cash', 'coin', 'dollar', 'yuan', 'price', 'cost', 'value',
        'buy', 'sell', 'trade', 'business', 'company', 'factory', 'industry', 'product', 'service', 'market',
        'bank', 'banking', 'account', 'deposit', 'withdrawal', 'loan', 'credit', 'debit', 'interest', 'rate',
        'investment', 'investor', 'stock', 'share', 'bond', 'dividend', 'profit', 'loss', 'revenue', 'expense',
        'budget', 'finance', 'financial', 'economy', 'economic', 'growth', 'development', 'recession', 'depression', 'inflation',
        'unemployment', 'employment', 'job', 'career', 'profession', 'occupation', 'salary', 'wage', 'income', 'tax',
        // 科学
        'science', 'scientist', 'research', 'experiment', 'discovery', 'invention', 'technology', 'theory', 'hypothesis', 'evidence',
        'physics', 'chemistry', 'biology', 'mathematics', 'astronomy', 'geology', 'medicine', 'engineering', 'computer', 'internet',
        'laboratory', 'lab', 'equipment', 'instrument', 'tool', 'device', 'apparatus', 'machine', 'mechanism', 'system',
        'observation', 'data', 'analysis', 'synthesis', 'conclusion', 'result', 'finding', 'discovery', 'breakthrough', 'innovation',
        'molecule', 'atom', 'particle', 'element', 'compound', 'reaction', 'chemical', 'physical', 'biological', 'natural',
        'force', 'energy', 'power', 'motion', 'speed', 'velocity', 'acceleration', 'gravity', 'friction', 'resistance',
        // 历史
        'history', 'historical', 'ancient', 'modern', 'past', 'present', 'future', 'century', 'decade', 'year',
        'war', 'peace', 'battle', 'fight', 'victory', 'defeat', 'hero', 'leader', 'king', 'queen',
        'empire', 'kingdom', 'republic', 'democracy', 'monarchy', 'dictatorship', 'revolution', 'rebellion', 'uprising', 'revolt',
        'civilization', 'culture', 'society', 'civilization', 'ancient', 'medieval', 'renaissance', 'enlightenment', 'industrial', 'modern',
        'archaeology', 'archaeologist', 'artifact', 'relic', 'monument', 'ruin', 'excavation', 'discovery', 'preservation', 'restoration',
        // 艺术
        'art', 'artist', 'painting', 'drawing', 'sculpture', 'music', 'musician', 'song', 'dance', 'theater',
        'literature', 'writer', 'poet', 'novel', 'poem', 'story', 'character', 'plot', 'theme', 'style',
        'gallery', 'museum', 'exhibition', 'display', 'show', 'performance', 'concert', 'opera', 'ballet', 'drama',
        'creative', 'creativity', 'imagination', 'inspiration', 'expression', 'emotion', 'feeling', 'mood', 'atmosphere', 'ambiance',
        'technique', 'skill', 'talent', 'ability', 'mastery', 'proficiency', 'expertise', 'experience', 'practice', 'training'
    ],
    
    'grade9' => [
        // 成就和目标
        'achieve', 'accomplish', 'succeed', 'fail', 'challenge', 'obstacle', 'difficulty', 'problem', 'solution', 'method',
        'opportunity', 'chance', 'advantage', 'disadvantage', 'benefit', 'risk', 'danger', 'safety', 'security', 'protection',
        'goal', 'aim', 'target', 'purpose', 'intention', 'plan', 'strategy', 'tactic', 'approach', 'method',
        'ambition', 'aspiration', 'dream', 'vision', 'mission', 'objective', 'destination', 'journey', 'path', 'route',
        'progress', 'advancement', 'improvement', 'development', 'growth', 'evolution', 'transformation', 'change', 'transition',
        // 职业
        'career', 'profession', 'job', 'work', 'employ', 'employee', 'employer', 'salary', 'income', 'expense',
        'occupation', 'vocation', 'position', 'role', 'duty', 'responsibility', 'task', 'assignment', 'project', 'mission',
        'interview', 'application', 'resume', 'cv', 'qualification', 'certificate', 'diploma', 'degree', 'license', 'permit',
        'promotion', 'demotion', 'raise', 'bonus', 'benefit', 'pension', 'retirement', 'unemployment', 'employment', 'jobless',
        'workplace', 'office', 'workshop', 'factory', 'laboratory', 'studio', 'field', 'site', 'location', 'venue',
        // 教育
        'education', 'school', 'university', 'college', 'academy', 'institute', 'course', 'program', 'degree', 'diploma',
        'student', 'teacher', 'professor', 'lecturer', 'tutor', 'coach', 'trainer', 'instructor', 'mentor', 'guide',
        'curriculum', 'syllabus', 'textbook', 'reference', 'material', 'resource', 'library', 'database', 'archive', 'collection',
        'scholarship', 'grant', 'fellowship', 'bursary', 'tuition', 'fee', 'expense', 'cost', 'payment', 'funding',
        'research', 'study', 'investigation', 'inquiry', 'exploration', 'examination', 'analysis', 'evaluation', 'assessment',
        // 社会问题
        'issue', 'problem', 'challenge', 'crisis', 'conflict', 'dispute', 'argument', 'debate', 'discussion', 'negotiation',
        'poverty', 'wealth', 'rich', 'poor', 'inequality', 'discrimination', 'prejudice', 'bias', 'stereotype', 'stigma',
        'homelessness', 'hunger', 'starvation', 'malnutrition', 'disease', 'illness', 'epidemic', 'pandemic', 'health', 'care',
        'violence', 'crime', 'theft', 'robbery', 'murder', 'assault', 'abuse', 'neglect', 'exploitation', 'trafficking',
        'justice', 'injustice', 'fairness', 'unfairness', 'equality', 'inequality', 'rights', 'freedom', 'liberty', 'oppression',
        // 全球问题
        'global', 'international', 'worldwide', 'universal', 'national', 'local', 'regional', 'domestic', 'foreign', 'overseas',
        'climate', 'environment', 'pollution', 'conservation', 'sustainability', 'renewable', 'energy', 'resource', 'waste', 'recycle',
        'migration', 'immigration', 'emigration', 'refugee', 'asylum', 'displacement', 'resettlement', 'integration', 'assimilation',
        'terrorism', 'extremism', 'radicalization', 'violence', 'conflict', 'war', 'peace', 'diplomacy', 'negotiation', 'treaty',
        'trade', 'commerce', 'business', 'economy', 'market', 'exchange', 'import', 'export', 'tariff', 'quota'
    ],
    
    'grade10' => [
        // 分析和研究
        'analyze', 'evaluate', 'compare', 'contrast', 'examine', 'investigate', 'research', 'study', 'experiment', 'discover',
        'theory', 'hypothesis', 'evidence', 'proof', 'fact', 'opinion', 'argument', 'debate', 'discuss', 'conclude',
        'philosophy', 'psychology', 'sociology', 'anthropology', 'economics', 'politics', 'democracy', 'republic', 'monarchy', 'government',
        'synthesize', 'integrate', 'combine', 'merge', 'unite', 'connect', 'link', 'relate', 'associate', 'correlate',
        'interpret', 'explain', 'clarify', 'elucidate', 'illuminate', 'illustrate', 'demonstrate', 'show', 'reveal', 'expose',
        // 学术
        'academic', 'scholar', 'scholarship', 'thesis', 'dissertation', 'essay', 'article', 'journal', 'publication', 'citation',
        'literature', 'reference', 'source', 'document', 'record', 'archive', 'database', 'library', 'collection', 'resource',
        'bibliography', 'index', 'glossary', 'appendix', 'footnote', 'endnote', 'quotation', 'quote', 'paraphrase', 'summary',
        'abstract', 'introduction', 'body', 'conclusion', 'paragraph', 'sentence', 'clause', 'phrase', 'word', 'vocabulary',
        'terminology', 'jargon', 'slang', 'dialect', 'accent', 'pronunciation', 'grammar', 'syntax', 'semantics', 'pragmatics',
        // 科学方法
        'method', 'methodology', 'procedure', 'process', 'technique', 'approach', 'strategy', 'tactic', 'system', 'framework',
        'observation', 'experiment', 'hypothesis', 'theory', 'law', 'principle', 'concept', 'idea', 'notion', 'conception',
        'variable', 'constant', 'control', 'dependent', 'independent', 'quantitative', 'qualitative', 'empirical', 'theoretical',
        'data', 'datum', 'statistic', 'statistics', 'sample', 'population', 'survey', 'questionnaire', 'interview', 'observation',
        'measurement', 'calculation', 'computation', 'analysis', 'synthesis', 'evaluation', 'interpretation', 'conclusion', 'result',
        // 批判性思维
        'critical', 'thinking', 'reasoning', 'logic', 'rational', 'logical', 'analytical', 'systematic', 'methodical', 'scientific',
        'question', 'doubt', 'skepticism', 'criticism', 'critique', 'evaluation', 'assessment', 'judgment', 'conclusion', 'decision',
        'assumption', 'premise', 'conclusion', 'inference', 'deduction', 'induction', 'abduction', 'reasoning', 'argumentation',
        'fallacy', 'error', 'mistake', 'bias', 'prejudice', 'stereotype', 'generalization', 'oversimplification', 'overgeneralization',
        'validity', 'reliability', 'credibility', 'authenticity', 'accuracy', 'precision', 'consistency', 'coherence', 'clarity',
        // 知识领域
        'knowledge', 'wisdom', 'understanding', 'comprehension', 'insight', 'awareness', 'consciousness', 'perception', 'cognition', 'intelligence',
        'learning', 'education', 'instruction', 'teaching', 'training', 'coaching', 'mentoring', 'guidance', 'supervision', 'direction',
        'expertise', 'proficiency', 'competence', 'mastery', 'skill', 'ability', 'talent', 'gift', 'aptitude', 'capacity',
        'memory', 'recall', 'recognition', 'retention', 'forgetting', 'remembering', 'memorization', 'recollection', 'reminiscence'
    ],
    
    'grade11' => [
        // 文学
        'literature', 'novel', 'poetry', 'drama', 'fiction', 'nonfiction', 'author', 'writer', 'character', 'plot',
        'theme', 'symbol', 'metaphor', 'imagery', 'narrative', 'dialogue', 'description', 'analysis', 'interpretation', 'criticism',
        'academic', 'scholar', 'research', 'thesis', 'dissertation', 'essay', 'article', 'journal', 'publication', 'citation',
        'genre', 'style', 'form', 'structure', 'content', 'context', 'subtext', 'subplot', 'foreshadowing', 'flashback',
        'protagonist', 'antagonist', 'hero', 'heroine', 'villain', 'narrator', 'narrative', 'perspective', 'point', 'view',
        'setting', 'atmosphere', 'mood', 'tone', 'voice', 'diction', 'syntax', 'rhythm', 'meter', 'rhyme',
        // 高级词汇
        'sophisticated', 'complex', 'intricate', 'elaborate', 'detailed', 'comprehensive', 'thorough', 'extensive', 'profound', 'deep',
        'abstract', 'concrete', 'specific', 'general', 'universal', 'particular', 'unique', 'distinct', 'different', 'similar',
        'ambiguous', 'unambiguous', 'explicit', 'implicit', 'overt', 'covert', 'obvious', 'subtle', 'nuanced', 'refined',
        'sophisticated', 'elegant', 'graceful', 'polished', 'refined', 'cultivated', 'educated', 'learned', 'erudite', 'scholarly',
        // 表达和沟通
        'express', 'communicate', 'convey', 'transmit', 'deliver', 'present', 'demonstrate', 'illustrate', 'explain', 'clarify',
        'persuade', 'convince', 'influence', 'affect', 'impact', 'effect', 'consequence', 'result', 'outcome', 'conclusion',
        'articulate', 'eloquent', 'fluent', 'fluency', 'coherence', 'cohesion', 'clarity', 'precision', 'accuracy', 'exactness',
        'rhetoric', 'rhetorical', 'persuasion', 'argumentation', 'debate', 'discussion', 'discourse', 'dialogue', 'conversation',
        // 学术写作
        'writing', 'composition', 'essay', 'thesis', 'dissertation', 'paper', 'article', 'report', 'review', 'summary',
        'paragraph', 'sentence', 'phrase', 'clause', 'word', 'vocabulary', 'terminology', 'jargon', 'slang', 'dialect',
        'draft', 'revision', 'editing', 'proofreading', 'formatting', 'citation', 'reference', 'bibliography', 'footnote', 'endnote',
        'coherence', 'cohesion', 'unity', 'organization', 'structure', 'outline', 'framework', 'skeleton', 'blueprint', 'plan',
        'introduction', 'body', 'conclusion', 'transition', 'connection', 'link', 'bridge', 'transitional', 'connective',
        // 文学分析
        'analyze', 'interpret', 'evaluate', 'critique', 'examine', 'explore', 'investigate', 'study', 'research', 'examine',
        'deconstruct', 'reconstruct', 'synthesize', 'integrate', 'combine', 'merge', 'unite', 'connect', 'relate', 'associate',
        'compare', 'contrast', 'juxtapose', 'parallel', 'analogy', 'metaphor', 'simile', 'personification', 'alliteration', 'assonance',
        'irony', 'sarcasm', 'satire', 'parody', 'allegory', 'fable', 'parable', 'myth', 'legend', 'folklore'
    ],
    
    'grade12' => [
        // 高等教育
        'university', 'college', 'academic', 'scholarship', 'tuition', 'degree', 'bachelor', 'master', 'doctor', 'professor',
        'admission', 'application', 'interview', 'recommendation', 'transcript', 'diploma', 'certificate', 'qualification', 'expertise', 'specialization',
        'career', 'profession', 'vocation', 'occupation', 'employment', 'internship', 'apprenticeship', 'mentorship', 'leadership', 'management',
        'undergraduate', 'graduate', 'postgraduate', 'doctoral', 'phd', 'mba', 'bachelor', 'master', 'doctorate', 'philosophy',
        'curriculum', 'syllabus', 'course', 'program', 'major', 'minor', 'elective', 'required', 'prerequisite', 'core',
        'semester', 'quarter', 'trimester', 'academic', 'year', 'term', 'session', 'class', 'lecture', 'seminar',
        // 高级学术
        'research', 'investigation', 'inquiry', 'exploration', 'examination', 'analysis', 'synthesis', 'evaluation', 'assessment', 'appraisal',
        'methodology', 'framework', 'paradigm', 'model', 'theory', 'hypothesis', 'concept', 'principle', 'doctrine', 'philosophy',
        'empirical', 'theoretical', 'quantitative', 'qualitative', 'mixed', 'methods', 'experimental', 'observational', 'longitudinal', 'cross',
        'sectional', 'case', 'study', 'survey', 'questionnaire', 'interview', 'focus', 'group', 'ethnography', 'phenomenology',
        'validity', 'reliability', 'credibility', 'transferability', 'dependability', 'confirmability', 'trustworthiness', 'rigor', 'quality',
        // 专业领域
        'discipline', 'field', 'domain', 'area', 'subject', 'topic', 'theme', 'focus', 'emphasis', 'priority',
        'specialization', 'expertise', 'proficiency', 'competence', 'mastery', 'skill', 'ability', 'talent', 'gift', 'aptitude',
        'interdisciplinary', 'multidisciplinary', 'transdisciplinary', 'cross', 'disciplinary', 'collaboration', 'cooperation', 'integration',
        'expert', 'specialist', 'generalist', 'practitioner', 'professional', 'amateur', 'novice', 'beginner', 'intermediate', 'advanced',
        // 职业发展
        'development', 'growth', 'progress', 'advancement', 'improvement', 'enhancement', 'refinement', 'perfection', 'excellence', 'achievement',
        'success', 'accomplishment', 'attainment', 'fulfillment', 'realization', 'actualization', 'materialization', 'manifestation', 'expression', 'demonstration',
        'promotion', 'advancement', 'career', 'ladder', 'hierarchy', 'position', 'rank', 'status', 'prestige', 'reputation',
        'networking', 'connection', 'contact', 'relationship', 'partnership', 'collaboration', 'alliance', 'association', 'affiliation',
        'mentor', 'mentee', 'protégé', 'apprentice', 'trainee', 'supervisor', 'supervisee', 'colleague', 'peer', 'counterpart',
        // 未来规划
        'future', 'prospect', 'potential', 'possibility', 'opportunity', 'chance', 'probability', 'likelihood', 'expectation', 'anticipation',
        'plan', 'strategy', 'tactic', 'approach', 'method', 'technique', 'procedure', 'process', 'system', 'framework',
        'goal', 'objective', 'target', 'aim', 'purpose', 'intention', 'ambition', 'aspiration', 'dream', 'vision',
        'roadmap', 'blueprint', 'outline', 'skeleton', 'structure', 'architecture', 'design', 'plan', 'scheme', 'project',
        'milestone', 'benchmark', 'indicator', 'measure', 'metric', 'kpi', 'key', 'performance', 'indicator', 'success',
        'factor', 'risk', 'mitigation', 'contingency', 'backup', 'alternative', 'option', 'choice', 'decision', 'commitment'
    ]
    ];
}
