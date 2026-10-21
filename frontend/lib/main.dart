import 'package:flutter/material.dart';
import 'models/destination.dart';
import 'services/api_client.dart';
import 'screens/destination_details.dart';
import 'screens/preferences.dart';
import 'screens/itinerary.dart';
import 'widgets/brand.dart';
import 'widgets/destination_card.dart';

void main() => runApp(const TripGenieApp());

class TripGenieApp extends StatelessWidget {
  final ApiClient? api;
  const TripGenieApp({super.key, this.api});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'TripGenie',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: teal,
        primary: teal,
        surface: Colors.white,
      ),
      scaffoldBackgroundColor: paper,
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFFF2F4EF),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        contentPadding: const EdgeInsets.all(16),
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 18),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 17),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
    ),
    home: TripGenieHome(api: api),
  );
}

class TripGenieHome extends StatefulWidget {
  final ApiClient? api;
  const TripGenieHome({super.key, this.api});
  @override
  State<TripGenieHome> createState() => _TripGenieHomeState();
}

class _TripGenieHomeState extends State<TripGenieHome> {
  late ApiClient _api;
  Map<String, dynamic>? _options;
  DiscoveryPage? _discovery;
  String? _startupError;
  String? _discoveryError;
  String? _matchError;
  String? _planError;
  bool _loading = true;
  bool _discoverLoading = false;
  bool _matchLoading = false;
  bool _planLoading = false;
  int _page = 0;
  int _cataloguePage = 1;
  int _discoverySequence = 0;
  final _search = TextEditingController();
  final _matchAnchor = GlobalKey();
  String? _state;
  String? _interest;
  Destination? _inspiration;
  Destination? _planning;
  List<Recommendation>? _recommendations;
  Map<String, dynamic> _lastPreferences = {};
  TripPlan? _plan;

  @override
  void initState() {
    super.initState();
    _api = widget.api ?? ApiClient();
    _initialize();
  }

  @override
  void dispose() {
    if (widget.api == null) {
      _api.close();
    }
    _search.dispose();
    super.dispose();
  }

  Future<void> _initialize() async {
    setState(() {
      _loading = true;
      _startupError = null;
    });
    try {
      final responses = await Future.wait([_api.options(), _api.discover()]);
      if (!mounted) {
        return;
      }
      setState(() {
        _options = responses[0] as Map<String, dynamic>;
        _discovery = responses[1] as DiscoveryPage;
        _loading = false;
      });
    } catch (error) {
      if (mounted) {
        setState(() {
          _startupError = error is ApiException
              ? error.message
              : 'Something went wrong. Please try again.';
          _loading = false;
        });
      }
    }
  }

  Future<void> _discover({int page = 1}) async {
    final sequence = ++_discoverySequence;
    setState(() {
      _discoverLoading = true;
      _discoveryError = null;
    });
    try {
      final results = await _api.discover(
        query: _search.text,
        state: _state,
        interest: _interest,
        page: page,
      );
      if (!mounted || sequence != _discoverySequence) {
        return;
      }
      setState(() {
        _discovery = results;
        _cataloguePage = page;
        _discoverLoading = false;
      });
    } catch (error) {
      if (mounted && sequence == _discoverySequence) {
        setState(() {
          _discoverLoading = false;
          _discoveryError = error is ApiException
              ? error.message
              : 'Something went wrong. Please try again.';
        });
      }
    }
  }

  Future<void> _recommend(Map<String, dynamic> preferences) async {
    setState(() {
      _matchLoading = true;
      _matchError = null;
      _recommendations = null;
    });
    _lastPreferences = Map<String, dynamic>.from(preferences);
    try {
      final results = await _api.recommend(preferences);
      if (mounted) {
        setState(() {
          _recommendations = results;
          _matchLoading = false;
        });
        WidgetsBinding.instance.addPostFrameCallback((_) {
          final anchor = _matchAnchor.currentContext;
          if (mounted && _page == 1 && anchor != null) {
            Scrollable.ensureVisible(
              anchor,
              duration: const Duration(milliseconds: 350),
              alignment: 0,
            );
          }
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _matchError = error is ApiException
              ? error.message
              : 'Something went wrong. Please try again.';
          _matchLoading = false;
        });
      }
    }
  }

  Future<void> _planTrip(Destination destination) async {
    setState(() {
      _planning = destination;
      _page = 2;
      _planLoading = true;
      _planError = null;
      _plan = null;
    });
    try {
      final plan = await _api.itinerary(
        destination.id,
        (_lastPreferences['trip_days'] as num?)?.round() ?? 3,
        _lastPreferences['budget_tier'] as String? ?? 'budget',
        List<String>.from(_lastPreferences['interests'] as List? ?? []),
      );
      if (mounted) {
        setState(() {
          _plan = plan;
          _planLoading = false;
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _planError = error is ApiException
              ? error.message
              : 'Something went wrong. Please try again.';
          _planLoading = false;
        });
      }
    }
  }

  void _explore(Destination destination) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      showDragHandle: true,
      constraints: const BoxConstraints(maxWidth: 720),
      builder: (sheetContext) => DestinationDetails(
        destination: destination,
        api: _api,
        onPlan: () {
          Navigator.pop(sheetContext);
          _planTrip(destination);
        },
        onInspiration: () {
          Navigator.pop(sheetContext);
          setState(() {
            _inspiration = destination;
            _page = 1;
          });
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 1000;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: paper,
        surfaceTintColor: paper,
        toolbarHeight: 84,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(9),
              decoration: BoxDecoration(
                color: teal,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(
                Icons.auto_awesome,
                color: Colors.white,
                size: 23,
              ),
            ),
            const SizedBox(width: 12),
            const Expanded(
              child: Text(
                'TripGenie',
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -.7,
                  color: ink,
                ),
              ),
            ),
          ],
        ),
        actions: wide
            ? [
                for (var i = 0; i < 3; i++)
                  Padding(
                    padding: const EdgeInsets.only(right: 12),
                    child: TextButton(
                      onPressed: () => setState(() => _page = i),
                      child: Text(
                        ['Discover', 'Build a trip', 'Your itinerary'][i],
                        style: TextStyle(
                          color: _page == i ? teal : const Color(0xFF586C65),
                          fontWeight: _page == i
                              ? FontWeight.w800
                              : FontWeight.w500,
                        ),
                      ),
                    ),
                  ),
                const SizedBox(width: 20),
              ]
            : null,
      ),
      bottomNavigationBar: wide
          ? null
          : NavigationBar(
              selectedIndex: _page,
              onDestinationSelected: (i) => setState(() => _page = i),
              destinations: const [
                NavigationDestination(
                  icon: Icon(Icons.explore_outlined),
                  label: 'Discover',
                ),
                NavigationDestination(
                  icon: Icon(Icons.tune),
                  label: 'Build a trip',
                ),
                NavigationDestination(
                  icon: Icon(Icons.route_outlined),
                  label: 'Itinerary',
                ),
              ],
            ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _startupError != null
          ? Center(
              child: StatusPanel(
                title: 'Let’s reconnect',
                message: _startupError!,
                onRetry: _initialize,
              ),
            )
          : IndexedStack(
              index: _page,
              children: [
                _scroll(_discoveryView()),
                _scroll(_preferencesView()),
                _scroll(_itineraryView()),
              ],
            ),
    );
  }

  Widget _scroll(Widget child) => SingleChildScrollView(
    child: Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 1240),
        child: Padding(
          padding: EdgeInsets.symmetric(
            horizontal: MediaQuery.sizeOf(context).width < 600 ? 18 : 32,
            vertical: 20,
          ),
          child: child,
        ),
      ),
    ),
  );
  Widget _discoveryView() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      LayoutBuilder(
        builder: (context, constraints) {
          final wide = constraints.maxWidth >= 760;
          return Container(
            clipBehavior: Clip.antiAlias,
            decoration: BoxDecoration(
              color: const Color(0xFFE6EDDF),
              borderRadius: BorderRadius.circular(24),
            ),
            child: Row(
              children: [
                Expanded(
                  flex: 3,
                  child: Padding(
                    padding: EdgeInsets.all(wide ? 36 : 24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'GO SOMEWHERE THAT FEELS LIKE YOU',
                          style: TextStyle(
                            fontSize: 10,
                            letterSpacing: 1.5,
                            color: teal,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'Your next\nIndia story.',
                          style: TextStyle(
                            fontFamily: 'Georgia',
                            fontSize: wide ? 52 : 40,
                            height: 1.12,
                            color: ink,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          'Coastal calm, mountain air, or a city full of stories.\nFind a place that fits your kind of journey.',
                          style: TextStyle(
                            height: 1.6,
                            color: Color(0xFF586C65),
                          ),
                        ),
                        const SizedBox(height: 24),
                        FilledButton.icon(
                          onPressed: () => setState(() => _page = 1),
                          icon: const Icon(Icons.arrow_forward),
                          label: const Text('Find my next trip'),
                        ),
                        const SizedBox(height: 16),
                        Text(
                          '${_options!['destination_count']} destinations · Built around your preferences',
                          style: const TextStyle(fontSize: 12, color: teal),
                        ),
                      ],
                    ),
                  ),
                ),
                if (wide)
                  const Expanded(
                    flex: 2,
                    child: SizedBox(
                      height: 350,
                      child: Landscape(interests: ['beach']),
                    ),
                  ),
              ],
            ),
          );
        },
      ),
      const SizedBox(height: 36),
      const SectionHeading(
        eyebrow: 'Explore the possibilities',
        title: 'A little inspiration goes a long way.',
        subtitle:
            'Browse the catalogue, discover what makes each place special, and make it your own.',
      ),
      LayoutBuilder(
        builder: (context, constraints) {
          final search = TextField(
            key: const Key('searchInput'),
            controller: _search,
            onSubmitted: (_) => _discover(),
            decoration: InputDecoration(
              hintText: 'Search destinations or experiences',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: IconButton(
                tooltip: 'Search',
                onPressed: () => _discover(),
                icon: const Icon(Icons.arrow_forward),
              ),
            ),
          );
          final state = DropdownButtonFormField<String>(
            initialValue: _state,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'State / location'),
            items: [
              const DropdownMenuItem<String>(
                value: null,
                child: Text('All of India'),
              ),
              ...List<String>.from(_options!['states'] as List).map(
                (s) => DropdownMenuItem(
                  value: s,
                  child: Text(s, overflow: TextOverflow.ellipsis),
                ),
              ),
            ],
            onChanged: (v) {
              setState(() => _state = v);
              _discover();
            },
          );
          return constraints.maxWidth < 640
              ? Column(children: [search, const SizedBox(height: 12), state])
              : Row(
                  children: [
                    Expanded(flex: 2, child: search),
                    const SizedBox(width: 16),
                    Expanded(child: state),
                  ],
                );
        },
      ),
      const SizedBox(height: 16),
      Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [null, 'beach', 'nature', 'heritage', 'wildlife', 'adventure']
            .map(
              (t) => ChoiceChip(
                label: Text(t == null ? 'All experiences' : label(t)),
                selected: _interest == t,
                onSelected: (_) {
                  setState(() => _interest = t);
                  _discover();
                },
              ),
            )
            .toList(),
      ),
      const SizedBox(height: 22),
      if (_discoverLoading)
        const Padding(
          padding: EdgeInsets.all(48),
          child: Center(child: CircularProgressIndicator()),
        )
      else if (_discoveryError != null)
        StatusPanel(
          title: 'Could not load destinations',
          message: _discoveryError!,
          onRetry: () => _discover(),
        )
      else if (_discovery!.destinations.isEmpty)
        const StatusPanel(
          title: 'No places found yet',
          message: 'Try a broader search or another state.',
        )
      else
        DestinationGrid(
          destinations: _discovery!.destinations,
          onExplore: _explore,
          onPlan: _planTrip,
        ),
      const SizedBox(height: 24),
      Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          IconButton(
            tooltip: 'Previous page',
            onPressed: _cataloguePage > 1 && !_discoverLoading
                ? () => _discover(page: _cataloguePage - 1)
                : null,
            icon: const Icon(Icons.chevron_left),
          ),
          Expanded(
            child: Text(
              'Page $_cataloguePage · ${_discovery!.total} destinations',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 13),
            ),
          ),
          IconButton(
            tooltip: 'Next page',
            onPressed:
                _cataloguePage * 12 < _discovery!.total && !_discoverLoading
                ? () => _discover(page: _cataloguePage + 1)
                : null,
            icon: const Icon(Icons.chevron_right),
          ),
        ],
      ),
      const SizedBox(height: 20),
      const Text(
        'Travel information is from the Indian Tourism Dataset on Kaggle. Confirm current costs and local conditions before booking.',
        style: TextStyle(fontSize: 12, color: Color(0xFF586C65)),
      ),
    ],
  );
  Widget _preferencesView() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const SectionHeading(
        eyebrow: 'Less searching, more discovering',
        title: 'A trip that fits you.',
        subtitle:
            'Tell us what you love, when you’re going, and the budget you have in mind.',
      ),
      PreferencesPanel(
        options: _options!,
        inspiration: _inspiration,
        loading: _matchLoading,
        onClearInspiration: () => setState(() => _inspiration = null),
        onSubmit: _recommend,
      ),
      const SizedBox(height: 32),
      if (_matchError != null)
        StatusPanel(
          title: 'Could not find your matches',
          message: _matchError!,
          onRetry: () => _recommend(_lastPreferences),
        ),
      if (_recommendations != null) ...[
        KeyedSubtree(
          key: _matchAnchor,
          child: SectionHeading(
            eyebrow: 'Made for your journey',
            title: 'Your destination shortlist.',
            subtitle:
                '${_recommendations!.length} unique matches. Explore the score breakdown to see how each place fits.',
          ),
        ),
        if (_recommendations!.isEmpty)
          const StatusPanel(
            title: 'Let’s open up the possibilities',
            message:
                'Try a higher budget, a different season, or turn off strict preferences.',
          )
        else
          DestinationGrid(
            destinations: _recommendations!.map((r) => r.destination).toList(),
            recommendations: _recommendations,
            onExplore: _explore,
            onPlan: _planTrip,
          ),
      ],
    ],
  );
  Widget _itineraryView() {
    if (_planLoading) {
      return const Padding(
        padding: EdgeInsets.all(60),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_planError != null) {
      return StatusPanel(
        title: 'Could not build your trip',
        message: _planError!,
        onRetry: () => _planTrip(_planning!),
      );
    }
    if (_plan != null) {
      return ItineraryView(plan: _plan!);
    }
    return const StatusPanel(
      title: 'Your next story starts with a place',
      message:
          'Choose “Plan trip” on a destination to build a flexible, day-by-day itinerary.',
    );
  }
}
