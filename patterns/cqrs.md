# CQRS — Code Review Checklist

- **Command/query separation**: commands mutate state and return no data; queries return data and have no side effects
- **Consistent projections**: read models updated correctly when write-side state changes
