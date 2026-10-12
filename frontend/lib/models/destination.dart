class Destination {
  final int id;
  final String name;
  final String state;
  final String region;
  final String description;
  final List<String> interests;
  final List<String> seasons;
  final List<String> attractions;
  final List<String> activities;
  final double costLow;
  final double costHigh;
  final double idealDays;
  final String accessibility;

  const Destination({
    required this.id,
    required this.name,
    required this.state,
    required this.region,
    required this.description,
    required this.interests,
    required this.seasons,
    required this.attractions,
    required this.activities,
    required this.costLow,
    required this.costHigh,
    required this.idealDays,
    required this.accessibility,
  });

  factory Destination.fromJson(Map<String, dynamic> json) {
    final cost = json['daily_cost'] as Map<String, dynamic>;
    final duration = json['duration'] as Map<String, dynamic>;
    return Destination(
      id: json['id'] as int,
      name: json['name'] as String,
      state: json['state'] as String,
      region: json['region'] as String,
      description: json['description'] as String,
      interests: List<String>.from(json['interests'] as List),
      seasons: List<String>.from(json['best_seasons'] as List),
      attractions: List<String>.from(json['attractions'] as List),
      activities: List<String>.from(json['activities'] as List),
      costLow: (cost['low'] as num).toDouble(),
      costHigh: (cost['high'] as num).toDouble(),
      idealDays: (duration['ideal'] as num).toDouble(),
      accessibility: json['accessibility'] as String,
    );
  }
}

class Recommendation {
  final Destination destination;
  final double score;
  final Map<String, dynamic> breakdown;
  const Recommendation(this.destination, this.score, this.breakdown);
  factory Recommendation.fromJson(Map<String, dynamic> json) => Recommendation(
    Destination.fromJson(json['destination'] as Map<String, dynamic>),
    (json['score'] as num).toDouble(),
    json['breakdown'] as Map<String, dynamic>,
  );
}

class DiscoveryPage {
  final List<Destination> destinations;
  final int total;
  const DiscoveryPage(this.destinations, this.total);
}

class TripPlan {
  final Map<String, dynamic> data;
  const TripPlan(this.data);
  String get name => data['destination_name'] as String;
  List<Map<String, dynamic>> get days =>
      (data['days'] as List).cast<Map<String, dynamic>>();
  List<String> get warnings => List<String>.from(data['warnings'] as List);
}
