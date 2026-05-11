import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/constants/colors.dart';
import '../../../providers/missing_person_provider.dart';
import '../../../models/missing_person_model.dart';
import '../../../models/enums.dart';

class MyCasesScreen extends StatefulWidget {
  const MyCasesScreen({super.key});

  @override
  State<MyCasesScreen> createState() => _MyCasesScreenState();
}

class _MyCasesScreenState extends State<MyCasesScreen> {
  String _selectedFilter = 'All';

  List<MissingPersonModel> _filterCases(List<MissingPersonModel> cases) {
    if (_selectedFilter == 'All') return cases;
    final status = CaseStatus.values.firstWhere(
      (s) => s.displayName == _selectedFilter,
      orElse: () => CaseStatus.active,
    );
    return cases.where((c) => c.status == status).toList();
  }

  @override
  Widget build(BuildContext context) {
    final missingPersonProvider = context.watch<MissingPersonProvider>();
    final filteredCases = _filterCases(missingPersonProvider.myCases);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('My Cases',
            style: TextStyle(
                color: AppColors.bodyText, fontWeight: FontWeight.bold)),
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        actions: [
          IconButton(
            onPressed: () => missingPersonProvider.fetchMyCases(),
            icon: const Icon(Icons.refresh, color: AppColors.bodyText),
          ),
        ],
      ),
      body: Column(
        children: [
          Container(
            color: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 10),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  _buildFilterChip('All'),
                  _buildFilterChip('Active'),
                  _buildFilterChip('Found'),
                  _buildFilterChip('Closed'),
                ],
              ),
            ),
          ),
          Expanded(
            child: missingPersonProvider.isLoading
                ? const Center(child: CircularProgressIndicator())
                : filteredCases.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.assignment_late_outlined,
                                size: 64, color: Colors.grey[400]),
                            const SizedBox(height: 16),
                            Text(
                              _selectedFilter == 'All'
                                  ? 'No cases reported yet'
                                  : 'No $_selectedFilter cases found',
                              style: TextStyle(
                                  color: Colors.grey[600], fontSize: 16),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: filteredCases.length,
                        itemBuilder: (context, index) {
                          final person = filteredCases[index];
                          return _buildCaseCard(context, person);
                        },
                      ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => Navigator.pushNamed(context, '/report'),
        backgroundColor: AppColors.primaryBlue,
        child: const Icon(Icons.add, color: Colors.white),
      ),
    );
  }

  Widget _buildFilterChip(String label) {
    final isSelected = _selectedFilter == label;
    return Container(
      margin: const EdgeInsets.only(right: 8),
      child: FilterChip(
        label: Text(label),
        selected: isSelected,
        onSelected: (v) {
          setState(() {
            _selectedFilter = label;
          });
        },
        backgroundColor: Colors.grey[100],
        selectedColor: AppColors.primaryBlue.withValues(alpha: 0.2),
        labelStyle: TextStyle(
          color: isSelected ? AppColors.primaryBlue : Colors.grey[700],
          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
        ),
      ),
    );
  }

  Widget _buildCaseCard(BuildContext context, MissingPersonModel person) {
    final statusStr = person.status.displayName;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withValues(alpha: 0.05),
              blurRadius: 10,
              offset: const Offset(0, 4))
        ],
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.all(12),
        leading: CircleAvatar(
          radius: 30,
          backgroundColor: const Color(0xFFE2E8F0),
          backgroundImage: (person.photos != null && person.photos!.isNotEmpty)
              ? NetworkImage(person.photos!.first)
              : null,
          child: (person.photos == null || person.photos!.isEmpty)
              ? const Icon(Icons.person, color: Colors.grey)
              : null,
        ),
        title: Text(person.fullName,
            style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: person.status == CaseStatus.active
                        ? Colors.orange[50]
                        : (person.status == CaseStatus.found
                            ? Colors.green[50]
                            : Colors.grey[100]),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    statusStr,
                    style: TextStyle(
                      color: person.status == CaseStatus.active
                          ? Colors.orange
                          : (person.status == CaseStatus.found
                              ? Colors.green
                              : Colors.grey),
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                if (person.lastSeenDatetime != null)
                  Text(
                      '${person.age ?? '?'} yrs • ${_getFormattedDate(person.lastSeenDatetime!)}',
                      style: const TextStyle(fontSize: 12, color: Colors.grey)),
              ],
            ),
          ],
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: () =>
            Navigator.pushNamed(context, '/case-details', arguments: person),
      ),
    );
  }

  String _getFormattedDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year}';
  }
}
