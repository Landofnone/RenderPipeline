#ifndef RP_POINTER_SLOT_STORAGE
#define RP_POINTER_SLOT_STORAGE

#include "pandabase.h"
#include <array>

/**
 * @brief Class to keep a list of pointers and nullpointers.
 * @details This class stores a fixed size list of pointers, whereas pointers
 *   may be a nullptr as well. It provides functionality to find free slots,
 *   and also to find free consecutive slots, as well as taking care of reserving slots.
 * 
 * @tparam T* Pointer-Type
 * @tparam SIZE Size of the storage
 */
template < typename T, int SIZE >
class PointerSlotStorage {
    
public:

    /**
     * @brief Constructs a new PointerSlotStorage
     * @details This constructs a new PointerSlotStorage, with all slots
     *   initialized to a nullptr.
     */
    PointerSlotStorage() {
        _data.fill(NULL);
        _max_index = 0;
    }

    /**
     * @brief Returns the maximum index of the container
     * @details This returns the greatest index of any element which is not zero.
     *   This can be useful for iterating the container, since all elements
     *   coming after the returned index are guaranteed to be a nullptr.
     * @return Maximum index of the container
     */
    size_t get_max_index() const {
        return _max_index;
    }

    /**
     * @brief Finds a free slot
     * @details This finds the first slot which is a nullptr and returns it.
     *   This is most likely useful in combination with reserve_slot.
     *   
     *   When no slot found was found, #slot will be undefined, and false will
     *   be returned.
     *   
     * @param slot Output-Variable, slot will be stored there
     * @return true if a slot was found, otherwise false
     */
    bool find_slot(size_t &slot) const {
        for (size_t i = 0; i < SIZE; ++i) {
            if (_data[i] == NULL) {
                slot = i;
                return true;
            }
        }
        return false;
    }

    /**
     * @brief Finds free consecutive slots
     * @details This behaves like find_slot, but it tries to find a slot
     *   after which <num_consecutive-1> free slots follow as well.
     *   
     *   When no slot found was found, #slot will be undefined, and false will
     *   be returned.
     * 
     * @param slot Output-Variable, index of the first slot of the consecutive
     *   slots will be stored there.
     * @param num_consecutive Amount of consecutive slots to find, including the
     *   first slot.
     * 
     * @return true if consecutive slots were found, otherwise false. 
     */
    bool find_consecutive_slots(size_t &slot, size_t num_consecutive) const {
        for (size_t i = 0; i < SIZE; ++i) {
            bool any_taken = false;
            for (size_t k = 0; !any_taken && k < num_consecutive; ++i) {
                any_taken = _data[i + k] == NULL;
            }
            if (!any_taken) {
                slot = i;
                return true;
            }
        }
        return false;
    }

    /**
     * @brief Frees an allocated slot
     * @details This frees an allocated slot. If the slot was already freed before,
     *   this method throws an assertion.
     * 
     * @param slot Slot to free
     */
    void free_slot(size_t slot) {
        nassertv(slot >= 0 && slot < SIZE);
        nassertv(_data[slot] != NULL); // Slot was already empty!
        _data[slot] = NULL;
    }

    /**
     * @brief Frees consecutive allocated slots
     * @details This behaves like PointerSlotStorage::free_slot, but deletes
     *   consecutive slots. 
     * 
     * @param slot Start of the consecutive slots to free
     * @param num_consecutive Number of consecutive slots
     */
    void free_consecutive_slots(size_t slot, size_t num_consecutive) {
        for (size_t i = slot; i < slot + num_consecutive; ++i) {
            free_slot(i);
        }
    }

    /**
     * @brief Reserves a slot
     * @details This reserves a slot by storing a pointer in it. If the slot
     *   was already taken, throws an assertion.
     *   If the ptr is a nullptr, also throws an assertion.
     *   If the slot was out of bounds, also throws an assertion.
     * 
     * @param slot Slot to reserve
     * @param ptr Pointer to store
     */
    void reserve_slot(size_t slot, T ptr) {
        nassertv(slot >= 0 && slot < SIZE);
        nassertv(_data[slot] == NULL); // Slot already taken!
        nassertv(ptr != NULL); // nullptr passed as argument!
        _data[slot] = ptr;
    }

    typedef array<T, SIZE> InternalContainer;

    /**
     * @brief Returns an iterator to the begin of the container
     * @details This returns an iterator to the beginning of the container 
     * @return Begin-Iterator
     */
    InternalContainer::iterator begin() {
        return _data.begin();
    }

    /**
     * @brief Returns an iterator to the end of the container
     * @details This returns an iterator to the end of the iterator. This only
     *   iterates to PointerSlotStorage::get_max_index()
     * @return [description]
     */
    InternalContainer::iterator end() {
        return std::advance(_data.begin(), _max_index);
    }

private:
    size_t _max_index;
    InternalContainer _data;
};

#endif // RP_POINTER_SLOT_STORAGE