package com.example.complex;

import com.example.simple.Simple;
import java.util.Collection;
import java.util.Map;
import java.util.HashMap;
import java.util.Optional;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Base repository interface.
 */
public interface Repository<T, ID> {
    Optional<T> findById(ID id);
    Collection<T> findAll();
    T save(T entity);
    void delete(ID id);
}

/**
 * Abstract base service with generic implementation.
 */
public abstract class BaseService<T> {

    protected final Map<Integer, T> store = new HashMap<>();

    public Optional<T> find(int id) {
        return Optional.ofNullable(store.get(id));
    }

    public abstract T create(String name);
}

/**
 * Annotated concrete service implementing both the interface and extending the base.
 */
@Service
@Transactional
public class ComplexService extends BaseService<Simple> implements Repository<Simple, Integer> {

    private int nextId = 1;

    public ComplexService() {
        super();
    }

    @Override
    public Optional<Simple> findById(Integer id) {
        return find(id);
    }

    @Override
    public Collection<Simple> findAll() {
        return store.values();
    }

    @Override
    public Simple save(Simple entity) {
        store.put(nextId++, entity);
        return entity;
    }

    @Override
    public void delete(Integer id) {
        store.remove(id);
    }

    @Override
    public Simple create(String name) {
        Simple s = Simple.of(name);
        return save(s);
    }

    /**
     * Method with high cyclomatic complexity.
     */
    public String classify(Simple item) {
        if (item == null) {
            return "null";
        }
        int v = item.getValue();
        String result;
        if (v < 0) {
            result = "negative";
        } else if (v == 0) {
            result = "zero";
        } else if (v < 10) {
            result = "small";
        } else if (v < 100) {
            result = "medium";
        } else if (v < 1000) {
            result = "large";
        } else {
            result = "huge";
        }
        return (item.getName() != null && !item.getName().isEmpty())
                ? item.getName() + "_" + result
                : result;
    }
}

/**
 * Enum with constants and fields.
 */
public enum Status {
    ACTIVE("active"),
    INACTIVE("inactive"),
    PENDING("pending");

    private final String label;

    Status(String label) {
        this.label = label;
    }

    public String getLabel() {
        return label;
    }
}
