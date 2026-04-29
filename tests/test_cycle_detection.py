from app.crud import would_create_cycle


def test_self_cycle():
    assert would_create_cycle({}, 1, 1) is True


def test_simple_no_cycle():
    adj = {2: {1}}  # 2 depends on 1
    # add 3 -> 2 (3 depends on 2): no cycle
    assert would_create_cycle(adj, 3, 2) is False


def test_transitive_cycle():
    # 2 depends on 1, 3 depends on 2.  Adding 1 -> 3 creates a cycle.
    adj = {2: {1}, 3: {2}}
    assert would_create_cycle(adj, 1, 3) is True


def test_diamond_no_cycle():
    # 2->1, 3->1, 4->2, 4->3 ; add 5->4 fine
    adj = {2: {1}, 3: {1}, 4: {2, 3}}
    assert would_create_cycle(adj, 5, 4) is False
